"""
PerteDocsTG - Vues Déclarations (corrigé + nouvelles fonctionnalités)
"""

from typing import Any, Dict
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, View
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q
from django.utils import timezone
import logging

from .models import Declaration, DocumentType, StatusHistory, DocumentFound
from .forms import (
    DeclarationStep1Form, DeclarationStep2Form, DeclarationStep3Form,
    DeclarationStep4Form, DeclarationStep5Form, DeclarationSearchForm,
)
from documents.models import Attachment
from audit.models import AuditLog

logger = logging.getLogger(__name__)


def _fire_notification(declaration_id: str, notification_type: str):
    """Lance une notification Celery ou en mode synchrone si pas de broker."""
    from notifications.tasks import send_declaration_notification, send_declaration_notification_sync
    try:
        send_declaration_notification.delay(declaration_id, notification_type)
    except Exception as exc:
        logger.warning('Broker indisponible, exécution synchrone: %s', exc)
        try:
            send_declaration_notification_sync(declaration_id, notification_type)
        except Exception as exc2:
            logger.error('Notification échouée: %s', exc2)


def _generate_receipt(declaration_id: str):
    """Génère le récépissé PDF (Celery ou synchrone)."""
    from notifications.tasks import generate_receipt_pdf, generate_receipt_for_declaration
    try:
        generate_receipt_pdf.delay(declaration_id)
    except Exception as exc:
        logger.warning('Broker indisponible, génération synchrone récépissé: %s', exc)
        try:
            generate_receipt_for_declaration(declaration_id)
        except Exception as exc2:
            logger.exception('Génération récépissé échouée: %s', exc2)


def _require_agent(user):
    if not (user.is_agent or user.is_administrator):
        raise Http404


def _get_declaration_for_agent(pk):
    return get_object_or_404(Declaration, pk=pk)


def _ensure_in_progress(declaration, user) -> bool:
    """Passe la déclaration en traitement si elle vient d'être soumise."""
    if declaration.status == 'submitted':
        declaration.assigned_agent = user
        declaration.save(update_fields=['assigned_agent', 'updated_at'])
        return declaration.transition_to('in_progress', user=user)
    return declaration.status in ('in_progress', 'under_review')


class DeclarationWizardView(LoginRequiredMixin, View):
    """Formulaire multi-étapes de déclaration."""

    template_names = {
        1: 'declarations/wizard/step1.html',
        2: 'declarations/wizard/step2.html',
        3: 'declarations/wizard/step3.html',
        4: 'declarations/wizard/step4.html',
        5: 'declarations/wizard/step5.html',
    }
    form_classes = {
        1: DeclarationStep1Form,
        2: DeclarationStep2Form,
        3: DeclarationStep3Form,
        4: DeclarationStep4Form,
        5: DeclarationStep5Form,
    }

    def dispatch(self, request, *args, **kwargs):
        self.declaration = self._resolve_declaration(request)
        return super().dispatch(request, *args, **kwargs)

    def _resolve_declaration(self, request, declaration_id=None):
        """Retrouve la déclaration brouillon en cours (session, POST ou dernier brouillon)."""
        decl_id = declaration_id or request.session.get('current_declaration_id')
        if request.method == 'POST':
            posted_id = request.POST.get('declaration_id')
            if posted_id:
                decl_id = posted_id

        declaration = None
        if decl_id:
            try:
                declaration = Declaration.objects.get(
                    id=decl_id, declarant=request.user, status='draft'
                )
            except (Declaration.DoesNotExist, ValueError):
                request.session.pop('current_declaration_id', None)

        if not declaration:
            declaration = (
                Declaration.objects.filter(declarant=request.user, status='draft')
                .order_by('-updated_at')
                .first()
            )

        if declaration:
            request.session['current_declaration_id'] = str(declaration.id)
            request.session.modified = True

        return declaration

    def get(self, request, step: int = 1):
        step = int(step)
        if step not in self.form_classes:
            return redirect('declarations:wizard', step=1)

        if step > 1 and not self.declaration:
            messages.warning(request, _('Veuillez commencer par l\'étape 1 pour créer votre déclaration.'))
            return redirect('declarations:wizard', step=1)

        initial = {}
        if step == 1 and not self.declaration:
            user = request.user
            initial = {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': str(user.phone) if user.phone else '',
                'prefecture': user.prefecture,
            }

        form_class = self.form_classes[step]
        if step == 5:
            form = form_class(initial={'declaration_id': self.declaration.id} if self.declaration else {})
        elif self.declaration and step in [1, 2, 3]:
            form = form_class(instance=self.declaration, initial=initial)
        else:
            form = form_class(initial=initial)

        return render(request, self.template_names[step], self._get_context(step, form))

    def post(self, request, step: int = 1):
        step = int(step)
        form_class = self.form_classes.get(step)
        if not form_class:
            return redirect('declarations:wizard', step=1)

        if step == 4:
            form = form_class(request.POST, request.FILES)
        elif step == 5:
            form = form_class(request.POST)
        elif self.declaration and step in [1, 2, 3]:
            form = form_class(request.POST, instance=self.declaration)
        else:
            form = form_class(request.POST)

        if form.is_valid():
            if step in [1, 2, 3]:
                decl = form.save(commit=False)
                decl.declarant = request.user
                if step == 1:
                    decl.full_name = f"{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}"
                decl.save()
                request.session['current_declaration_id'] = str(decl.id)
                request.session.modified = True
                self.declaration = decl
            elif step == 4:
                if not self.declaration:
                    messages.error(request, _('Aucune déclaration en cours. Reprenez depuis l\'étape 1.'))
                    return redirect('declarations:wizard', step=1)
                self._handle_attachments(request, form)
            elif step == 5:
                return self._finalize_declaration(request, form)

            next_step = step + 1
            return redirect('declarations:wizard', step=min(next_step, 5))

        return render(request, self.template_names[step], self._get_context(step, form))

    def _handle_attachments(self, request, form):
        if not self.declaration:
            return
        for field_name in ['attachment_1', 'attachment_2', 'attachment_3']:
            file = form.cleaned_data.get(field_name)
            if file:
                Attachment.objects.create(
                    declaration=self.declaration,
                    uploaded_by=request.user,
                    file=file,
                    original_name=file.name,
                    file_size=file.size,
                    mime_type=file.content_type,
                )

    def _finalize_declaration(self, request, form):
        decl = self.declaration or self._resolve_declaration(
            request, declaration_id=form.cleaned_data.get('declaration_id')
        )
        if not decl:
            messages.error(request, _('Aucune déclaration en cours. Reprenez depuis l\'étape 1.'))
            return redirect('declarations:wizard', step=1)

        decl.honor_declaration = True
        decl.electronic_signature = form.cleaned_data.get('signature_data', '')
        decl.signature_date = timezone.now()
        client_ip = AuditLog._get_client_ip(request)
        decl.ip_address = client_ip or None
        decl.save(update_fields=[
            'honor_declaration', 'electronic_signature', 'signature_date', 'ip_address', 'updated_at',
        ])

        if decl.transition_to('submitted', user=request.user):
            request.session.pop('current_declaration_id', None)
            request.session.modified = True
            _fire_notification(str(decl.id), 'declaration_submitted')
            AuditLog.log(
                action=AuditLog.Action.SUBMIT,
                user=request.user, obj=decl, request=request,
                notes=f'Déclaration {decl.declaration_number} soumise',
            )
            messages.success(
                request,
                _('Déclaration %(num)s soumise avec succès !') % {'num': decl.declaration_number}
            )
            return redirect('dashboard:home')

        messages.error(request, _('Erreur lors de la soumission. Veuillez réessayer.'))
        return redirect('declarations:wizard', step=5)

    def _get_context(self, step: int, form) -> Dict[str, Any]:
        ctx = {
            'form': form, 'step': step, 'total_steps': 5,
            'declaration': self.declaration,
            'steps': [
                {'num': 1, 'label': _('Informations'), 'icon': 'user'},
                {'num': 2, 'label': _('Document'), 'icon': 'document'},
                {'num': 3, 'label': _('Circonstances'), 'icon': 'map-pin'},
                {'num': 4, 'label': _('Pièces jointes'), 'icon': 'paperclip'},
                {'num': 5, 'label': _('Confirmation'), 'icon': 'check'},
            ],
        }
        if step == 1:
            from core.models import Region
            ctx['regions'] = Region.objects.filter(is_active=True).order_by('order', 'name')
            selected_region = None
            if getattr(form, 'instance', None) and getattr(form.instance, 'prefecture', None):
                selected_region = form.instance.prefecture.region_id
            ctx['selected_region'] = selected_region
        return ctx


class DeclarationListView(LoginRequiredMixin, ListView):
    template_name = 'declarations/list.html'
    context_object_name = 'declarations'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        qs = Declaration.objects.select_related('document_type', 'prefecture', 'assigned_agent', 'found_record')
        if not (user.is_administrator or user.is_agent):
            qs = qs.filter(declarant=user)

        form = DeclarationSearchForm(self.request.GET)
        if form.is_valid():
            if q := form.cleaned_data.get('query'):
                qs = qs.filter(
                    Q(declaration_number__icontains=q) | Q(full_name__icontains=q) |
                    Q(phone__icontains=q) | Q(email__icontains=q)
                )
            if s := form.cleaned_data.get('status'):
                qs = qs.filter(status=s)
            if dt := form.cleaned_data.get('document_type'):
                qs = qs.filter(document_type=dt)
            if df := form.cleaned_data.get('date_from'):
                qs = qs.filter(created_at__date__gte=df)
            if dt2 := form.cleaned_data.get('date_to'):
                qs = qs.filter(created_at__date__lte=dt2)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = DeclarationSearchForm(self.request.GET)
        ctx['total_count'] = self.get_queryset().count()
        ctx['declaration_statuses'] = Declaration.Status.choices
        ctx['document_types'] = DocumentType.objects.filter(is_active=True)
        return ctx


class DeclarationDetailView(LoginRequiredMixin, DetailView):
    template_name = 'declarations/detail.html'
    context_object_name = 'declaration'

    def get_queryset(self):
        user = self.request.user
        qs = Declaration.objects.select_related(
            'document_type', 'prefecture', 'declarant', 'assigned_agent', 'validated_by'
        ).prefetch_related('attachments', 'status_history__changed_by')
        if not (user.is_administrator or user.is_agent):
            qs = qs.filter(declarant=user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        decl = self.object
        ctx['status_history'] = decl.status_history.all().order_by('created_at')
        ctx['attachments'] = decl.attachments.all()
        try:
            ctx['receipt'] = decl.receipt
        except Exception:
            ctx['receipt'] = None
        try:
            ctx['found_record'] = decl.found_record
        except Exception:
            ctx['found_record'] = None
        AuditLog.log(action=AuditLog.Action.VIEW, user=self.request.user, obj=decl, request=self.request)
        return ctx


class DeclarationConfirmationView(LoginRequiredMixin, DetailView):
    template_name = 'declarations/confirmation.html'
    context_object_name = 'declaration'

    def get_queryset(self):
        return Declaration.objects.filter(declarant=self.request.user)


# ── Vue Agent : signaler document retrouvé ────────────────────────────────────

@login_required
def agent_mark_document_found(request, pk: str):
    """L'agent signale qu'un document déclaré perdu a été retrouvé."""
    if not (request.user.is_agent or request.user.is_administrator):
        raise Http404

    declaration = get_object_or_404(
        Declaration.objects.select_related('declarant', 'document_type'),
        pk=pk, status__in=['validated', 'submitted', 'in_progress']
    )

    if request.method == 'POST':
        from datetime import timedelta
        found_by = request.POST.get('found_by', '').strip()
        found_location = request.POST.get('found_location', '').strip()
        notes = request.POST.get('notes', '').strip()
        days = int(request.POST.get('collection_days', 30))

        found, created = DocumentFound.objects.get_or_create(
            declaration=declaration,
            defaults={
                'found_by': found_by,
                'found_location': found_location,
                'notes': notes,
                'registered_by': request.user,
                'collection_deadline': timezone.now().date() + timedelta(days=days),
            }
        )
        if not created:
            found.found_by = found_by
            found.found_location = found_location
            found.notes = notes
            found.collection_deadline = timezone.now().date() + timedelta(days=days)
            found.save()

        # Notifier le citoyen
        from notifications.tasks import notify_document_found
        try:
            notify_document_found.delay(str(declaration.id), str(found.id))
        except Exception:
            notify_document_found(str(declaration.id), str(found.id))

        AuditLog.log(
            action='update', user=request.user, obj=declaration, request=request,
            notes=f'Document retrouvé signalé pour {declaration.declaration_number}',
        )
        messages.success(request, _('✅ Document signalé comme retrouvé. Le citoyen a été notifié.'))
        return redirect('declarations:detail', pk=pk)

    return render(request, 'declarations/agent_found_form.html', {'declaration': declaration})


@login_required
def agent_mark_collected(request, pk: str):
    """L'agent confirme que le citoyen est venu récupérer son document."""
    if not (request.user.is_agent or request.user.is_administrator):
        raise Http404
    declaration = get_object_or_404(Declaration, pk=pk)
    try:
        found = declaration.found_record
        found.mark_collected()
        messages.success(request, _('✅ Document marqué comme récupéré par le citoyen.'))
    except DocumentFound.DoesNotExist:
        messages.error(request, _('Aucun signalement de retrouvaille pour cette déclaration.'))
    return redirect('declarations:detail', pk=pk)


@login_required
def agent_take_charge(request, pk: str):
    """L'agent prend en charge une déclaration soumise."""
    _require_agent(request.user)
    if request.method != 'POST':
        return redirect('declarations:detail', pk=pk)

    declaration = _get_declaration_for_agent(pk)
    if declaration.status != 'submitted':
        messages.warning(request, _('Cette déclaration n\'est plus en attente de prise en charge.'))
        return redirect('declarations:detail', pk=pk)

    declaration.assigned_agent = request.user
    declaration.save(update_fields=['assigned_agent', 'updated_at'])
    if declaration.transition_to('in_progress', user=request.user):
        AuditLog.log(
            action='update', user=request.user, obj=declaration, request=request,
            notes=f'Prise en charge de {declaration.declaration_number}',
        )
        messages.success(request, _('Dossier pris en charge. Vous pouvez maintenant valider, rejeter ou demander un complément.'))
    else:
        messages.error(request, _('Impossible de prendre en charge ce dossier.'))
    return redirect('declarations:detail', pk=pk)


@login_required
def agent_validate(request, pk: str):
    """Valide une déclaration et génère le récépissé PDF avec QR code."""
    _require_agent(request.user)
    if request.method != 'POST':
        return redirect('declarations:detail', pk=pk)

    declaration = _get_declaration_for_agent(pk)
    if not _ensure_in_progress(declaration, request.user):
        messages.error(request, _('Validation impossible depuis le statut actuel.'))
        return redirect('declarations:detail', pk=pk)

    notes = request.POST.get('notes', '').strip()
    if declaration.transition_to('validated', user=request.user, notes=notes):
        _fire_notification(str(declaration.id), 'declaration_validated')
        try:
            from notifications.tasks import generate_receipt_for_declaration
            generate_receipt_for_declaration(str(declaration.id))
        except Exception as exc:
            logger.exception('Génération récépissé après validation: %s', exc)
            messages.warning(
                request,
                _('Déclaration validée, mais le récépissé PDF n\'a pas pu être généré. Réessayez le téléchargement.')
            )
            return redirect('declarations:detail', pk=pk)
        AuditLog.log(
            action='update', user=request.user, obj=declaration, request=request,
            notes=f'Validation de {declaration.declaration_number}',
        )
        messages.success(request, _('Déclaration validée. Le récépissé PDF avec QR code est prêt — le citoyen a été notifié.'))
    else:
        messages.error(request, _('Impossible de valider cette déclaration.'))
    return redirect('declarations:detail', pk=pk)


@login_required
def agent_reject(request, pk: str):
    """Rejette une déclaration avec motif obligatoire."""
    _require_agent(request.user)
    if request.method != 'POST':
        return redirect('declarations:detail', pk=pk)

    declaration = _get_declaration_for_agent(pk)
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, _('Le motif de rejet est obligatoire.'))
        return redirect('declarations:detail', pk=pk)

    if declaration.status == 'submitted':
        declaration.assigned_agent = request.user
        declaration.save(update_fields=['assigned_agent', 'updated_at'])
        declaration.transition_to('in_progress', user=request.user)

    if declaration.transition_to('rejected', user=request.user, notes=reason):
        _fire_notification(str(declaration.id), 'declaration_rejected')
        AuditLog.log(
            action='update', user=request.user, obj=declaration, request=request,
            notes=f'Rejet de {declaration.declaration_number}: {reason[:100]}',
        )
        messages.success(request, _('Déclaration rejetée. Le citoyen a été notifié.'))
    else:
        messages.error(request, _('Impossible de rejeter cette déclaration.'))
    return redirect('declarations:detail', pk=pk)


@login_required
def agent_request_complement(request, pk: str):
    """Demande un complément d'informations au citoyen."""
    _require_agent(request.user)
    if request.method != 'POST':
        return redirect('declarations:detail', pk=pk)

    declaration = _get_declaration_for_agent(pk)
    complement = request.POST.get('complement', '').strip()
    if not complement:
        messages.error(request, _('Précisez le complément demandé.'))
        return redirect('declarations:detail', pk=pk)

    if declaration.status == 'submitted':
        declaration.assigned_agent = request.user
        declaration.save(update_fields=['assigned_agent', 'updated_at'])

    if declaration.transition_to('complement_requested', user=request.user, notes=complement):
        _fire_notification(str(declaration.id), 'complement_requested')
        AuditLog.log(
            action='update', user=request.user, obj=declaration, request=request,
            notes=f'Complément demandé pour {declaration.declaration_number}',
        )
        messages.success(request, _('Complément demandé. Le citoyen a été notifié.'))
    else:
        messages.error(request, _('Impossible de demander un complément pour ce dossier.'))
    return redirect('declarations:detail', pk=pk)


@login_required
def declaration_download_receipt(request, pk: str):
    from documents.models import Receipt
    from documents.services import ReceiptService

    if request.user.is_agent or request.user.is_administrator:
        declaration = get_object_or_404(
            Declaration.objects.select_related('document_type', 'validated_by'),
            pk=pk, status='validated',
        )
    else:
        declaration = get_object_or_404(
            Declaration.objects.filter(declarant=request.user).select_related(
                'document_type', 'validated_by'
            ),
            pk=pk, status='validated',
        )

    try:
        receipt = Receipt.objects.filter(declaration=declaration).first()
        if not receipt or not receipt.file:
            receipt = ReceiptService.generate_receipt(declaration)

        if not receipt.file:
            messages.error(request, _('Le fichier PDF n\'a pas pu être généré.'))
            return redirect('declarations:detail', pk=pk)

        receipt.download_count += 1
        receipt.save(update_fields=['download_count'])
        AuditLog.log(action=AuditLog.Action.DOWNLOAD, user=request.user, obj=receipt, request=request)

        with receipt.file.open('rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="recepisse-{declaration.declaration_number}.pdf"'
        )
        return response
    except Exception as exc:
        logger.exception('Téléchargement récépissé impossible pour %s: %s', pk, exc)
        messages.error(request, _('Récépissé non disponible.'))
        return redirect('declarations:detail', pk=pk)


@login_required
def ajax_get_prefectures(request):
    region_id = request.GET.get('region_id')
    from core.models import Prefecture
    prefectures = Prefecture.objects.filter(region_id=region_id, is_active=True).values('id', 'name')
    return JsonResponse({'prefectures': list(prefectures)})


@login_required
def ajax_declaration_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    user = request.user
    qs = Declaration.objects.select_related('document_type').filter(
        Q(declaration_number__icontains=query) | Q(full_name__icontains=query)
    )
    if not (user.is_administrator or user.is_agent):
        qs = qs.filter(declarant=user)
    results = [{
        'id': str(d.id), 'number': d.declaration_number, 'name': d.full_name,
        'document_type': d.document_type.name if d.document_type else '—', 'status': d.status,
        'status_label': d.get_status_display(), 'url': d.get_absolute_url(),
    } for d in qs[:10]]
    return JsonResponse({'results': results})

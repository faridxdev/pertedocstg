"""
PerteDocsTG - Vues Core
"""

from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import connection
from django.conf import settings
from django.core.cache import cache

from declarations.models import Declaration, DocumentType


class LandingPageView(TemplateView):
    """Page d'accueil / Landing page publique."""

    template_name = 'core/landing.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['document_types'] = DocumentType.objects.filter(is_active=True).order_by('order')
        ctx['stats'] = {
            'total_declarations': Declaration.objects.exclude(status='draft').count(),
            'validated': Declaration.objects.filter(status='validated').count(),
            'avg_hours': 48,
        }
        # Labels par défaut si la base est vide
        ctx['default_doc_labels'] = ["CNI", "Passeport", "Permis", "Électeur", "Naissance", "Consulaire", "Séjour", "Diplôme", "Carte grise", "Autre"]
        ctx['steps'] = [
            {
                'num': '01',
                'icon': 'user-circle',
                'title': _('Créez votre compte'),
                'desc': _('Inscription rapide avec votre email ou numéro de téléphone'),
                'color': 'green',
            },
            {
                'num': '02',
                'icon': 'document-text',
                'title': _('Remplissez le formulaire'),
                'desc': _('Décrivez le document perdu et les circonstances de la perte'),
                'color': 'yellow',
            },
            {
                'num': '03',
                'icon': 'paper-clip',
                'title': _('Joignez vos documents'),
                'desc': _('Téléchargez les pièces justificatives requises'),
                'color': 'red',
            },
            {
                'num': '04',
                'icon': 'check-circle',
                'title': _('Recevez votre récépissé'),
                'desc': _('Téléchargez votre récépissé officiel après validation'),
                'color': 'green',
            },
        ]
        return ctx


class VerificationPublicView(View):
    """Page de vérification publique des récépissés."""

    template_name = 'core/verification.html'

    def get(self, request, token: str):
        try:
            declaration = Declaration.objects.select_related(
                'document_type', 'declarant', 'validated_by'
            ).get(verification_token=token)

            found_record = None
            try:
                found_record = declaration.found_record
            except Exception:
                pass

            context = {
                'valid': True,
                'declaration': declaration,
                'found_record': found_record,
                'token': token,
            }
        except Declaration.DoesNotExist:
            context = {
                'valid': False,
                'token': token,
                'error': _('Ce code de vérification est invalide ou n\'existe pas dans notre système.'),
            }
        return render(request, self.template_name, context)


class AboutView(TemplateView):
    template_name = 'core/about.html'


class ContactView(TemplateView):
    template_name = 'core/contact.html'


class FAQView(TemplateView):
    template_name = 'core/faq.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['faqs'] = [
            {
                'question': _('Quels documents puis-je déclarer perdus sur cette plateforme ?'),
                'answer': _('Vous pouvez déclarer la perte de : CNI, Passeport, Permis de conduire, '
                            'Carte d\'électeur, Acte de naissance, Carte consulaire, Carte de séjour, '
                            'Diplôme, Carte grise, et tout autre document administratif.'),
            },
            {
                'question': _('Combien de temps prend le traitement de ma déclaration ?'),
                'answer': _('Le traitement standard est de 48 à 72 heures ouvrables. '
                            'Vous recevrez des notifications par email et SMS à chaque étape.'),
            },
            {
                'question': _('Mon récépissé est-il juridiquement valide ?'),
                'answer': _('Oui. Le récépissé délivré par PerteDocsTG est un document officiel '
                            'reconnu par les administrations togolaises. Il comporte un QR Code '
                            'de vérification et une signature électronique.'),
            },
            {
                'question': _('Que faire si ma déclaration est rejetée ?'),
                'answer': _('En cas de rejet, vous recevrez une notification avec le motif détaillé. '
                            'Vous pourrez soumettre une nouvelle déclaration avec les corrections nécessaires.'),
            },
            {
                'question': _('Comment vérifier l\'authenticité d\'un récépissé ?'),
                'answer': _('Scannez le QR Code présent sur le récépissé ou visitez '
                            'pertedocs.tg/verification/ et entrez le numéro de vérification.'),
            },
            {
                'question': _('L\'inscription est-elle gratuite ?'),
                'answer': _('Oui, l\'utilisation de la plateforme PerteDocsTG est entièrement gratuite '
                            'pour tous les citoyens togolais.'),
            },
        ]
        return ctx


class LegalView(TemplateView):
    template_name = 'core/legal.html'


class MaintenanceView(TemplateView):
    template_name = 'core/maintenance.html'


def health_check(request):
    """Endpoint de santé pour le monitoring."""
    checks = {'status': 'ok', 'timestamp': timezone.now().isoformat()}

    # DB check
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
        checks['status'] = 'degraded'

    # Redis check
    try:
        cache.set('health_check', '1', 5)
        checks['cache'] = 'ok'
    except Exception as e:
        checks['cache'] = f'error: {str(e)}'

    return JsonResponse(checks)

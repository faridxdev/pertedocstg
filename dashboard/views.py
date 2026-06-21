"""
PerteDocsTG — Vues Dashboard (citoyen / agent / admin séparés)
"""

from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg, ExpressionWrapper, F, DurationField
from django.utils import timezone
from datetime import timedelta, date
import csv
import io
import json

from declarations.models import Declaration, DocumentType
from accounts.models import User
from notifications.models import Notification


@login_required
def redirect_dashboard(request):
    """Redirige vers le bon dashboard selon le rôle."""
    user = request.user
    if user.is_administrator:
        return redirect('dashboard:admin')
    if user.is_agent:
        return redirect('dashboard:agent_home')
    return redirect('dashboard:citizen')


class CitizenDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard citoyen."""
    template_name = 'dashboard/citizen.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        decls = Declaration.objects.filter(declarant=user)

        ctx['stats'] = {
            'total': decls.count(),
            'validated': decls.filter(status='validated').count(),
            'in_progress': decls.filter(status__in=['submitted', 'in_progress', 'under_review']).count(),
            'rejected': decls.filter(status='rejected').count(),
            'draft': decls.filter(status='draft').count(),
        }
        ctx['recent_declarations'] = decls.select_related(
            'document_type', 'found_record'
        ).order_by('-created_at')[:6]
        ctx['notifications'] = Notification.objects.filter(
            user=user, is_read=False
        ).order_by('-created_at')[:5]
        return ctx


class AgentDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard agent."""
    template_name = 'dashboard/agent_home.html'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and
                (request.user.is_agent or request.user.is_administrator)):
            return redirect('dashboard:citizen')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()

        ctx['pending_declarations'] = Declaration.objects.filter(
            status__in=['submitted', 'in_progress']
        ).select_related('declarant', 'document_type').order_by('submitted_at')[:20]

        ctx['my_declarations'] = Declaration.objects.filter(
            assigned_agent=self.request.user
        ).select_related('declarant', 'document_type').order_by('-updated_at')[:10]

        ctx['stats'] = {
            'pending': Declaration.objects.filter(status='submitted').count(),
            'in_progress': Declaration.objects.filter(status='in_progress').count(),
            'validated_today': Declaration.objects.filter(status='validated', processed_at__date=today).count(),
            'rejected_today': Declaration.objects.filter(status='rejected', processed_at__date=today).count(),
        }
        return ctx


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard administrateur complet avec KPIs."""
    template_name = 'dashboard/admin.html'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_administrator):
            return redirect('dashboard:citizen')
        export = request.GET.get('export')
        if export in ('csv', 'excel', 'pdf'):
            period = request.GET.get('period', 'month')
            if export == 'pdf':
                return self._export_pdf(period)
            return self._export_csv(period, excel=(export == 'excel'))
        return super().dispatch(request, *args, **kwargs)

    def _period_start(self, period: str):
        today = timezone.now().date()
        starts = {
            'day': today,
            'week': today - timedelta(days=7),
            'month': today.replace(day=1),
            'year': today.replace(month=1, day=1),
        }
        return starts.get(period, today.replace(day=1))

    def _declarations_for_period(self, period: str):
        start = self._period_start(period)
        return Declaration.objects.filter(
            created_at__date__gte=start
        ).select_related('document_type', 'declarant', 'prefecture__region')

    def _export_csv(self, period: str, excel: bool = False):
        decls = self._declarations_for_period(period)
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=';' if excel else ',')
        writer.writerow([
            'N° déclaration', 'Déclarant', 'Email', 'Téléphone', 'Type document',
            'Statut', 'Région', 'Date création', 'Date soumission', 'Date traitement',
        ])
        for d in decls.order_by('-created_at'):
            writer.writerow([
                d.declaration_number,
                d.full_name,
                d.email,
                d.phone,
                d.document_type.name if d.document_type else '',
                d.get_status_display(),
                d.prefecture.region.name if d.prefecture and d.prefecture.region else '',
                d.created_at.strftime('%d/%m/%Y %H:%M'),
                d.submitted_at.strftime('%d/%m/%Y %H:%M') if d.submitted_at else '',
                d.processed_at.strftime('%d/%m/%Y %H:%M') if d.processed_at else '',
            ])
        content = buffer.getvalue()
        ext = 'xls' if excel else 'csv'
        mime = 'application/vnd.ms-excel' if excel else 'text/csv; charset=utf-8'
        response = HttpResponse(content_type=mime)
        response.content = content.encode('utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="pertedocs-export-{period}.{ext}"'
        return response

    def _export_pdf(self, period: str):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        decls = self._declarations_for_period(period)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm)
        styles = getSampleStyleSheet()
        story = [
            Paragraph('PerteDocsTG — Export statistiques', styles['Title']),
            Paragraph(f'Période : {period}', styles['Normal']),
            Spacer(1, 0.5 * cm),
        ]
        total = decls.count()
        validated = decls.filter(status='validated').count()
        rejected = decls.filter(status='rejected').count()
        pending = decls.filter(status__in=['submitted', 'in_progress', 'under_review']).count()
        summary = [
            ['Indicateur', 'Valeur'],
            ['Total déclarations', str(total)],
            ['Validées', str(validated)],
            ['Rejetées', str(rejected)],
            ['En attente', str(pending)],
        ]
        table = Table(summary, colWidths=[8 * cm, 4 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#006B3F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        story.append(table)
        doc.build(story)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="pertedocs-stats-{period}.pdf"'
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        week_start = today - timedelta(days=7)
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        all_decls = Declaration.objects.all()

        ctx['kpis'] = {
            'today': all_decls.filter(created_at__date=today).count(),
            'week': all_decls.filter(created_at__date__gte=week_start).count(),
            'month': all_decls.filter(created_at__date__gte=month_start).count(),
            'year': all_decls.filter(created_at__date__gte=year_start).count(),
            'total': all_decls.count(),
            'pending': all_decls.filter(status__in=['submitted', 'in_progress', 'under_review']).count(),
            'validated': all_decls.filter(status='validated').count(),
            'rejected': all_decls.filter(status='rejected').count(),
            'avg_processing_hours': self._avg_processing_time(),
        }

        ctx['by_document_type'] = list(
            all_decls.values('document_type__name')
            .annotate(count=Count('id')).order_by('-count')[:10]
        )
        ctx['by_status'] = list(all_decls.values('status').annotate(count=Count('id')))
        ctx['by_region'] = list(
            all_decls.filter(prefecture__isnull=False)
            .values('prefecture__region__name')
            .annotate(count=Count('id')).order_by('-count')
        )

        ctx['recent_declarations'] = all_decls.select_related(
            'declarant', 'document_type'
        ).order_by('-created_at')[:10]

        ctx['total_users'] = User.objects.filter(role='citizen').count()
        ctx['new_users_today'] = User.objects.filter(
            created_at__date=today, role='citizen'
        ).count()

        ctx['monthly_chart_data'] = json.dumps(self._monthly_chart())
        ctx['document_type_chart_data'] = json.dumps(self._doctype_chart())
        return ctx

    def _avg_processing_time(self) -> float:
        result = Declaration.objects.filter(
            status='validated',
            submitted_at__isnull=False,
            processed_at__isnull=False,
        ).annotate(
            duration=ExpressionWrapper(
                F('processed_at') - F('submitted_at'), output_field=DurationField()
            )
        ).aggregate(avg=Avg('duration'))
        avg = result.get('avg')
        return round(avg.total_seconds() / 3600, 1) if avg else 0

    def _monthly_chart(self) -> dict:
        labels, submitted, validated = [], [], []
        today = date.today()
        for i in range(11, -1, -1):
            m_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            m_end = (m_start + timedelta(days=32)).replace(day=1)
            labels.append(m_start.strftime('%b %Y'))
            submitted.append(Declaration.objects.filter(created_at__gte=m_start, created_at__lt=m_end).count())
            validated.append(Declaration.objects.filter(status='validated', processed_at__gte=m_start, processed_at__lt=m_end).count())
        return {
            'labels': labels,
            'datasets': [
                {'label': 'Soumises', 'data': submitted, 'borderColor': '#3B82F6', 'backgroundColor': 'rgba(59,130,246,0.08)', 'tension': 0.4, 'fill': True},
                {'label': 'Validées', 'data': validated, 'borderColor': '#006B3F', 'backgroundColor': 'rgba(0,107,63,0.08)', 'tension': 0.4, 'fill': True},
            ]
        }

    def _doctype_chart(self) -> dict:
        data = list(Declaration.objects.values('document_type__name').annotate(count=Count('id')).order_by('-count')[:8])
        return {
            'labels': [d['document_type__name'] for d in data],
            'data': [d['count'] for d in data],
            'colors': ['#006B3F', '#FFCE00', '#D21034', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444', '#6B7280'],
        }


@login_required
def api_dashboard_stats(request):
    """API JSON pour mise à jour dynamique des stats."""
    period = request.GET.get('period', 'month')
    today = timezone.now().date()
    starts = {
        'day': today,
        'week': today - timedelta(days=7),
        'month': today.replace(day=1),
        'year': today.replace(month=1, day=1),
    }
    start = starts.get(period, today.replace(day=1))

    qs = Declaration.objects.filter(created_at__date__gte=start)
    if request.user.is_citizen:
        qs = qs.filter(declarant=request.user)
    elif not request.user.is_administrator:
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    validated_qs = qs.filter(status='validated', submitted_at__isnull=False, processed_at__isnull=False)
    avg_result = validated_qs.annotate(
        duration=ExpressionWrapper(F('processed_at') - F('submitted_at'), output_field=DurationField())
    ).aggregate(avg=Avg('duration'))
    avg = avg_result.get('avg')
    avg_hours = round(avg.total_seconds() / 3600, 1) if avg else 0

    period_labels = {'day': "aujourd'hui", 'week': '7 derniers jours', 'month': 'ce mois', 'year': 'cette année'}

    return JsonResponse({
        'total': qs.count(),
        'validated': qs.filter(status='validated').count(),
        'rejected': qs.filter(status='rejected').count(),
        'pending': qs.filter(status__in=['submitted', 'in_progress', 'under_review']).count(),
        'today': qs.filter(created_at__date=today).count(),
        'avg_processing_hours': avg_hours,
        'period': period,
        'period_label': period_labels.get(period, period),
        'by_status': list(qs.values('status').annotate(count=Count('id'))),
    })

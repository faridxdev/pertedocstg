"""
PerteDocsTG — Audit : Vues et URLs
"""
from django.urls import path
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import AuditLog


class AuditLogListView(LoginRequiredMixin, ListView):
    """Liste des logs d'audit (admin seulement)."""
    template_name = 'audit/list.html'
    context_object_name = 'logs'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_administrator):
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user').order_by('-created_at')
        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action=action)
        user_id = self.request.GET.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['actions'] = AuditLog.Action.choices
        return ctx


app_name = 'audit'

urlpatterns = [
    path('logs/', AuditLogListView.as_view(), name='logs'),
]

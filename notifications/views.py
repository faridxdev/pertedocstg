"""
PerteDocsTG — Notifications : Vues et URLs
"""
from django.urls import path
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['unread_count'] = Notification.objects.filter(
            user=self.request.user, is_read=False
        ).count()
        return ctx


@login_required
def mark_all_read(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=405)


def notifications_context(request):
    """Context processor pour les notifications non lues."""
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}


app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='list'),
    path('marquer-lus/', mark_all_read, name='mark_all_read'),
]

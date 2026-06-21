from .models import Notification

def notifications_context(request):
    """Ajoute le nombre de notifications non lues au contexte de tous les templates."""
    if request.user.is_authenticated:
        return {
            'unread_notifications_count': Notification.objects.filter(
                user=request.user, is_read=False
            ).count()
        }
    return {'unread_notifications_count': 0}
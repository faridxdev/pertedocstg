from django.urls import path
from .views import NotificationListView, mark_all_read

app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='list'),
    path('marquer-lus/', mark_all_read, name='mark_all_read'),
]

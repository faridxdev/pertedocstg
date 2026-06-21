from django.urls import path
from .views import ProfileView, SettingsView, UpdatePreferencesView

app_name = 'accounts'

urlpatterns = [
    path('profile/', ProfileView.as_view(), name='profile'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('preferences/', UpdatePreferencesView.as_view(), name='preferences'),
]

"""
PerteDocsTG — Comptes : Vues
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth import get_user_model
import json

User = get_user_model()


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['declarations_count'] = user.declarations.count()
        ctx['validated_count'] = user.declarations.filter(status='validated').count()
        return ctx


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/settings.html'


class UpdatePreferencesView(LoginRequiredMixin, TemplateView):
    """Met à jour les préférences utilisateur via AJAX."""

    def post(self, request):
        try:
            data = json.loads(request.body)
            user = request.user
            if 'dark_mode' in data:
                user.dark_mode = bool(data['dark_mode'])
            if 'language' in data and data['language'] in ['fr', 'en', 'ee', 'kbp']:
                user.language = data['language']
            if 'email_notifications' in data:
                user.email_notifications = bool(data['email_notifications'])
            if 'sms_notifications' in data:
                user.sms_notifications = bool(data['sms_notifications'])
            user.save(update_fields=['dark_mode', 'language', 'email_notifications', 'sms_notifications'])
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

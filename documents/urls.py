"""
PerteDocsTG — URLs Documents
"""
from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from .models import Attachment

app_name = 'documents'


class AttachmentDownloadView(LoginRequiredMixin, View):
    """Téléchargement sécurisé d'une pièce jointe."""

    def get(self, request, pk):
        attachment = get_object_or_404(Attachment, pk=pk)
        # Vérifier que l'utilisateur a le droit
        if not (request.user.is_agent or request.user.is_administrator):
            if attachment.declaration.declarant != request.user:
                raise Http404
        return FileResponse(
            attachment.file,
            as_attachment=True,
            filename=attachment.original_name,
        )


urlpatterns = [
    path('attachment/<uuid:pk>/', AttachmentDownloadView.as_view(), name='download'),
]

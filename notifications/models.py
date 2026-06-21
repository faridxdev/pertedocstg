"""
PerteDocsTG - Modèles Notifications
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings


class Notification(models.Model):
    """Notifications internes aux utilisateurs."""

    class NotificationType(models.TextChoices):
        DECLARATION_SUBMITTED = 'declaration_submitted', _('Déclaration soumise')
        DECLARATION_VALIDATED = 'declaration_validated', _('Déclaration validée')
        DECLARATION_REJECTED = 'declaration_rejected', _('Déclaration rejetée')
        COMPLEMENT_REQUESTED = 'complement_requested', _('Complément demandé')
        RECEIPT_READY = 'receipt_ready', _('Récépissé disponible')
        DOCUMENT_FOUND = 'document_found', _('Document retrouvé')
        SYSTEM = 'system', _('Système')
        INFO = 'info', _('Information')
        WARNING = 'warning', _('Avertissement')

    class Channel(models.TextChoices):
        INTERNAL = 'internal', _('Interne')
        EMAIL = 'email', _('Email')
        SMS = 'sms', _('SMS')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications', verbose_name=_('Utilisateur')
    )
    declaration = models.ForeignKey(
        'declarations.Declaration', on_delete=models.CASCADE,
        null=True, blank=True, related_name='notifications'
    )

    notification_type = models.CharField(
        _('Type'), max_length=40, choices=NotificationType.choices
    )
    channel = models.CharField(
        _('Canal'), max_length=10, choices=Channel.choices, default=Channel.INTERNAL
    )
    title = models.CharField(_('Titre'), max_length=200)
    message = models.TextField(_('Message'))
    is_read = models.BooleanField(_('Lu'), default=False)
    read_at = models.DateTimeField(_('Lu le'), null=True, blank=True)
    sent = models.BooleanField(_('Envoyé'), default=False)
    sent_at = models.DateTimeField(_('Envoyé le'), null=True, blank=True)
    error_message = models.TextField(_('Erreur'), blank=True)

    created_at = models.DateTimeField(_('Créé le'), default=timezone.now)

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f'{self.title} → {self.user.get_full_name()}'

    def mark_as_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @property
    def icon(self) -> str:
        icons = {
            'declaration_submitted': 'paper-airplane',
            'declaration_validated': 'check-circle',
            'declaration_rejected': 'x-circle',
            'complement_requested': 'exclamation-circle',
            'receipt_ready': 'document-download',
            'system': 'cog',
            'info': 'information-circle',
            'warning': 'exclamation',
        }
        return icons.get(self.notification_type, 'bell')

    @property
    def color(self) -> str:
        colors = {
            'declaration_validated': 'green',
            'declaration_rejected': 'red',
            'complement_requested': 'yellow',
            'receipt_ready': 'blue',
            'warning': 'orange',
        }
        return colors.get(self.notification_type, 'gray')


class EmailLog(models.Model):
    """Journal des emails envoyés."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, null=True, blank=True
    )
    recipient_email = models.EmailField(_('Email destinataire'))
    subject = models.CharField(_('Sujet'), max_length=255)
    body_text = models.TextField(_('Corps texte'))
    body_html = models.TextField(_('Corps HTML'), blank=True)
    sent = models.BooleanField(_('Envoyé'), default=False)
    sent_at = models.DateTimeField(_('Envoyé le'), null=True, blank=True)
    error = models.TextField(_('Erreur'), blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _('Log Email')
        verbose_name_plural = _('Logs Emails')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.subject} → {self.recipient_email}'


class SMSLog(models.Model):
    """Journal des SMS envoyés."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, null=True, blank=True
    )
    recipient_phone = models.CharField(_('Téléphone destinataire'), max_length=20)
    message = models.TextField(_('Message'))
    sent = models.BooleanField(_('Envoyé'), default=False)
    sent_at = models.DateTimeField(_('Envoyé le'), null=True, blank=True)
    provider_response = models.JSONField(_('Réponse opérateur'), default=dict)
    error = models.TextField(_('Erreur'), blank=True)
    cost = models.DecimalField(_('Coût'), max_digits=10, decimal_places=4, default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _('Log SMS')
        verbose_name_plural = _('Logs SMS')
        ordering = ['-created_at']

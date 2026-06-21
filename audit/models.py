"""
PerteDocsTG - Modèles Audit et Traçabilité
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings


class AuditLog(models.Model):
    """Journal d'audit complet de toutes les actions."""

    class Action(models.TextChoices):
        LOGIN = 'login', _('Connexion')
        LOGOUT = 'logout', _('Déconnexion')
        LOGIN_FAILED = 'login_failed', _('Échec connexion')
        CREATE = 'create', _('Création')
        UPDATE = 'update', _('Modification')
        DELETE = 'delete', _('Suppression')
        VIEW = 'view', _('Consultation')
        DOWNLOAD = 'download', _('Téléchargement')
        SUBMIT = 'submit', _('Soumission')
        VALIDATE = 'validate', _('Validation')
        REJECT = 'reject', _('Rejet')
        EXPORT = 'export', _('Export')
        IMPORT = 'import', _('Import')
        PERMISSION_CHANGE = 'permission_change', _('Changement de permission')
        CONFIG_CHANGE = 'config_change', _('Changement de configuration')
        PASSWORD_CHANGE = 'password_change', _('Changement de mot de passe')
        TWO_FACTOR = 'two_factor', _('Authentification 2FA')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_logs', verbose_name=_('Utilisateur')
    )
    action = models.CharField(_('Action'), max_length=30, choices=Action.choices, db_index=True)

    # Objet concerné
    content_type = models.CharField(_('Type d\'objet'), max_length=100, blank=True)
    object_id = models.CharField(_('ID objet'), max_length=100, blank=True)
    object_repr = models.CharField(_('Représentation'), max_length=255, blank=True)

    # Données de changement
    changes = models.JSONField(_('Changements'), default=dict)

    # Contexte réseau
    ip_address = models.GenericIPAddressField(_('Adresse IP'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    referer = models.URLField(_('Referer'), blank=True)
    session_key = models.CharField(_('Session'), max_length=40, blank=True)

    # Résultat
    success = models.BooleanField(_('Succès'), default=True)
    error_message = models.TextField(_('Message d\'erreur'), blank=True)

    # Notes additionnelles
    notes = models.TextField(_('Notes'), blank=True)

    created_at = models.DateTimeField(_('Date'), default=timezone.now, db_index=True)

    class Meta:
        verbose_name = _('Log d\'audit')
        verbose_name_plural = _('Logs d\'audit')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self) -> str:
        user_str = self.user.get_full_name() if self.user else 'Anonyme'
        return f'[{self.created_at.strftime("%d/%m/%Y %H:%M")}] {user_str} - {self.get_action_display()}'

    @classmethod
    def log(cls, action: str, user=None, obj=None, changes: dict = None,
            request=None, success: bool = True, notes: str = '', error: str = '') -> 'AuditLog':
        """Méthode helper pour créer un log d'audit."""
        ip_address = None
        user_agent = ''
        referer = ''
        session_key = ''

        if request:
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            referer = request.META.get('HTTP_REFERER', '')[:200]
            if hasattr(request, 'session'):
                session_key = request.session.session_key or ''

        content_type = ''
        object_id = ''
        object_repr = ''
        if obj:
            content_type = type(obj).__name__
            object_id = str(getattr(obj, 'pk', ''))
            object_repr = str(obj)[:255]

        return cls.objects.create(
            user=user,
            action=action,
            content_type=content_type,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
            session_key=session_key,
            success=success,
            error_message=error,
            notes=notes,
        )

    @staticmethod
    def _get_client_ip(request) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

"""
PerteDocsTG - Modèles Documents et Pièces Jointes
"""

import uuid
import os
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.core.validators import FileExtensionValidator


def declaration_upload_path(instance, filename: str) -> str:
    """Détermine le chemin de stockage des pièces jointes."""
    declaration_id = str(instance.declaration.id)
    return f'declarations/{declaration_id[:2]}/{declaration_id}/{filename}'


def receipt_upload_path(instance, filename: str) -> str:
    return f'receipts/{instance.declaration.declaration_number}/{filename}'


class Attachment(models.Model):
    """Pièces jointes aux déclarations."""

    class AttachmentType(models.TextChoices):
        IDENTITY = 'identity', _('Pièce d\'identité')
        PROOF_ADDRESS = 'proof_address', _('Justificatif de domicile')
        PROOF_LOSS = 'proof_loss', _('Justificatif de perte')
        PHOTO = 'photo', _('Photo')
        OTHER = 'other', _('Autre')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    declaration = models.ForeignKey(
        'declarations.Declaration', on_delete=models.CASCADE,
        related_name='attachments', verbose_name=_('Déclaration')
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    attachment_type = models.CharField(
        _('Type'), max_length=20, choices=AttachmentType.choices, default=AttachmentType.OTHER
    )
    file = models.FileField(
        _('Fichier'), upload_to=declaration_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    original_name = models.CharField(_('Nom original'), max_length=255)
    file_size = models.PositiveIntegerField(_('Taille (octets)'), default=0)
    mime_type = models.CharField(_('Type MIME'), max_length=100, blank=True)
    checksum = models.CharField(_('Checksum SHA256'), max_length=64, blank=True)

    # Validation
    is_valid = models.BooleanField(_('Valide'), default=True)
    validation_notes = models.TextField(_('Notes de validation'), blank=True)
    is_virus_scanned = models.BooleanField(_('Antivirus passé'), default=False)
    virus_scan_result = models.CharField(_('Résultat scan'), max_length=50, blank=True)

    created_at = models.DateTimeField(_('Uploadé le'), default=timezone.now)

    class Meta:
        verbose_name = _('Pièce jointe')
        verbose_name_plural = _('Pièces jointes')
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.original_name} ({self.declaration.declaration_number})'

    def save(self, *args, **kwargs):
        if self.file and not self.checksum:
            self.checksum = self._compute_checksum()
        if self.file and not self.original_name:
            self.original_name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def _compute_checksum(self) -> str:
        import hashlib
        sha256 = hashlib.sha256()
        if self.file:
            for chunk in self.file.chunks():
                sha256.update(chunk)
        return sha256.hexdigest()

    @property
    def file_size_display(self) -> str:
        """Retourne la taille formatée."""
        size = self.file_size
        for unit in ['o', 'Ko', 'Mo', 'Go']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} To'

    @property
    def is_image(self) -> bool:
        return self.mime_type in ['image/jpeg', 'image/png', 'image/webp']

    @property
    def is_pdf(self) -> bool:
        return self.mime_type == 'application/pdf'


class Receipt(models.Model):
    """Récépissé officiel généré après validation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    declaration = models.OneToOneField(
        'declarations.Declaration', on_delete=models.CASCADE,
        related_name='receipt', verbose_name=_('Déclaration')
    )
    receipt_number = models.CharField(_('Numéro récépissé'), max_length=50, unique=True)
    file = models.FileField(_('Fichier PDF'), upload_to='receipts/', null=True, blank=True)
    qr_code_data = models.TextField(_('Données QR Code'), blank=True)
    qr_code_image = models.ImageField(_('Image QR Code'), upload_to='qrcodes/', null=True, blank=True)
    digital_signature = models.TextField(_('Signature numérique'), blank=True)
    issued_at = models.DateTimeField(_('Émis le'), default=timezone.now)
    expires_at = models.DateField(_('Expire le'), null=True, blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    download_count = models.PositiveIntegerField(_('Téléchargements'), default=0)

    class Meta:
        verbose_name = _('Récépissé')
        verbose_name_plural = _('Récépissés')
        ordering = ['-issued_at']

    def __str__(self) -> str:
        return f'Récépissé {self.receipt_number}'

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self._generate_receipt_number()
        super().save(*args, **kwargs)

    def _generate_receipt_number(self) -> str:
        import random, string
        year = timezone.now().year
        month = timezone.now().month
        suffix = ''.join(random.choices(string.digits, k=6))
        return f'REC-{year}{month:02d}-{suffix}'

    @property
    def is_valid(self) -> bool:
        if self.expires_at:
            return self.expires_at >= timezone.now().date()
        return True

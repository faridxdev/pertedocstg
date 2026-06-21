"""
PerteDocsTG - Modèles Déclarations de Perte
"""

import uuid
import hashlib
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.urls import reverse


def generate_declaration_number() -> str:
    """Génère un numéro unique de déclaration."""
    import random
    import string
    year = timezone.now().year
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=8))
    return f'TG-{year}-{suffix}'


class DocumentType(models.Model):
    """Types de documents pouvant être déclarés perdus."""

    TYPES = [
        ('cni', _('Carte Nationale d\'Identité')),
        ('passeport', _('Passeport')),
        ('permis_conduire', _('Permis de conduire')),
        ('carte_electeur', _('Carte d\'électeur')),
        ('acte_naissance', _('Acte de naissance')),
        ('carte_consulaire', _('Carte consulaire')),
        ('carte_sejour', _('Carte de séjour')),
        ('diplome', _('Diplôme')),
        ('carte_grise', _('Carte grise')),
        ('autre', _('Autre')),
    ]

    code = models.CharField(_('Code'), max_length=30, unique=True)
    name = models.CharField(_('Nom'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    icon = models.CharField(_('Icône'), max_length=50, default='document')
    requires_number = models.BooleanField(_('Nécessite un numéro'), default=True)
    processing_days = models.PositiveSmallIntegerField(_('Délai traitement (jours)'), default=3)
    is_active = models.BooleanField(_('Actif'), default=True)
    order = models.PositiveSmallIntegerField(_('Ordre'), default=0)

    class Meta:
        verbose_name = _('Type de document')
        verbose_name_plural = _('Types de documents')
        ordering = ['order', 'name']

    def __str__(self) -> str:
        return self.name


class Declaration(models.Model):
    """Déclaration de perte de document administratif."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        SUBMITTED = 'submitted', _('Soumis')
        IN_PROGRESS = 'in_progress', _('En cours')
        UNDER_REVIEW = 'under_review', _('En vérification')
        VALIDATED = 'validated', _('Validé')
        REJECTED = 'rejected', _('Rejeté')
        ARCHIVED = 'archived', _('Archivé')
        COMPLEMENT_REQUESTED = 'complement_requested', _('Complément demandé')

    class Nationality(models.TextChoices):
        TOGOLESE = 'TG', _('Togolaise')
        OTHER = 'OT', _('Autre')

    # Identifiants
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    declaration_number = models.CharField(
        _('Numéro de déclaration'), max_length=30, unique=True,
        db_index=True, blank=True
    )
    verification_token = models.CharField(
        _('Token de vérification'), max_length=64, unique=True, blank=True, db_index=True
    )

    # Relation utilisateur
    declarant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='declarations', verbose_name=_('Déclarant')
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_declarations',
        verbose_name=_('Agent assigné')
    )

    # Statut
    status = models.CharField(
        _('Statut'), max_length=30, choices=Status.choices, default=Status.DRAFT, db_index=True
    )

    # ─── Informations du déclarant ────────────────────────────────────────────
    full_name = models.CharField(_('Nom complet'), max_length=200)
    first_name = models.CharField(_('Prénom'), max_length=100)
    last_name = models.CharField(_('Nom de famille'), max_length=100)
    date_of_birth = models.DateField(_('Date de naissance'))
    place_of_birth = models.CharField(_('Lieu de naissance'), max_length=200)
    nationality = models.CharField(_('Nationalité'), max_length=100, default='Togolaise')
    phone = models.CharField(_('Téléphone'), max_length=20)
    email = models.EmailField(_('Email'))
    profession = models.CharField(_('Profession'), max_length=200, blank=True)
    address = models.TextField(_('Adresse'))
    prefecture = models.ForeignKey(
        'core.Prefecture', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='declarations', verbose_name=_('Préfecture')
    )

    # ─── Document perdu ───────────────────────────────────────────────────────
    document_type = models.ForeignKey(
        DocumentType, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='declarations', verbose_name=_('Type de document')
    )
    document_number = models.CharField(_('Numéro du document'), max_length=100, blank=True)
    document_issue_date = models.DateField(_('Date de délivrance'), null=True, blank=True)
    document_issue_place = models.CharField(_('Lieu de délivrance'), max_length=200, blank=True)
    document_authority = models.CharField(_('Autorité émettrice'), max_length=200, blank=True)

    # ─── Circonstances de la perte ────────────────────────────────────────────
    loss_date = models.DateField(_('Date estimée de perte'), null=True, blank=True)
    loss_place = models.CharField(_('Lieu de perte'), max_length=300, blank=True)
    loss_circumstances = models.TextField(_('Circonstances de perte'), blank=True)
    loss_description = models.TextField(_('Description détaillée'), blank=True)

    # ─── Déclaration sur l'honneur ────────────────────────────────────────────
    honor_declaration = models.BooleanField(_('Déclaration sur l\'honneur'), default=False)
    electronic_signature = models.TextField(_('Signature électronique'), blank=True)
    signature_date = models.DateTimeField(_('Date de signature'), null=True, blank=True)
    ip_address = models.GenericIPAddressField(_('Adresse IP'), null=True, blank=True)

    # ─── Traitement administratif ─────────────────────────────────────────────
    agent_notes = models.TextField(_('Notes de l\'agent'), blank=True)
    rejection_reason = models.TextField(_('Motif de rejet'), blank=True)
    complement_requested = models.TextField(_('Complément demandé'), blank=True)
    processing_started_at = models.DateTimeField(_('Traitement débuté le'), null=True, blank=True)
    processed_at = models.DateTimeField(_('Traité le'), null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='validated_declarations',
        verbose_name=_('Validé par')
    )

    # ─── Récépissé ────────────────────────────────────────────────────────────
    receipt_generated = models.BooleanField(_('Récépissé généré'), default=False)
    receipt_file = models.FileField(_('Fichier récépissé'), upload_to='receipts/', null=True, blank=True)
    receipt_generated_at = models.DateTimeField(_('Récépissé généré le'), null=True, blank=True)
    receipt_expires_at = models.DateField(_('Expiration récépissé'), null=True, blank=True)

    # ─── Timestamps ───────────────────────────────────────────────────────────
    created_at = models.DateTimeField(_('Créé le'), default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(_('Modifié le'), auto_now=True)
    submitted_at = models.DateTimeField(_('Soumis le'), null=True, blank=True)

    class Meta:
        verbose_name = _('Déclaration')
        verbose_name_plural = _('Déclarations')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['declaration_number']),
            models.Index(fields=['status']),
            models.Index(fields=['declarant', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['verification_token']),
        ]

    def __str__(self) -> str:
        return f'{self.declaration_number} - {self.full_name}'

    def save(self, *args, **kwargs) -> None:
        if not self.declaration_number:
            self.declaration_number = generate_declaration_number()
        if not self.verification_token:
            self.verification_token = self._generate_verification_token()
        if not self.full_name:
            self.full_name = f'{self.first_name} {self.last_name}'.strip()
        super().save(*args, **kwargs)

    def _generate_verification_token(self) -> str:
        import secrets
        return secrets.token_urlsafe(32)

    def get_absolute_url(self) -> str:
        return reverse('declarations:detail', kwargs={'pk': str(self.pk)})

    def get_verification_url(self) -> str:
        return reverse('core:verification', kwargs={'token': self.verification_token})

    @property
    def is_editable(self) -> bool:
        return self.status in [self.Status.DRAFT, self.Status.COMPLEMENT_REQUESTED]

    @property
    def found_record_safe(self):
        """Retourne le DocumentFound lié, ou None si absent (sûr pour les templates)."""
        try:
            return self.found_record
        except DocumentFound.DoesNotExist:
            return None

    @property
    def is_validated(self) -> bool:
        return self.status == self.Status.VALIDATED

    @property
    def status_color(self) -> str:
        colors = {
            'draft': 'gray',
            'submitted': 'blue',
            'in_progress': 'yellow',
            'under_review': 'purple',
            'validated': 'green',
            'rejected': 'red',
            'archived': 'gray',
            'complement_requested': 'orange',
        }
        return colors.get(self.status, 'gray')

    def transition_to(self, new_status: str, user=None, notes: str = '') -> bool:
        """Gère les transitions de statut avec validation."""
        allowed_transitions = {
            'draft': ['submitted'],
            'submitted': ['in_progress', 'complement_requested'],
            'in_progress': ['under_review', 'validated', 'rejected', 'complement_requested'],
            'under_review': ['validated', 'rejected', 'complement_requested'],
            'complement_requested': ['submitted'],
            'validated': ['archived'],
        }
        if new_status in allowed_transitions.get(self.status, []):
            old_status = self.status
            self.status = new_status
            if new_status == 'submitted' and not self.submitted_at:
                self.submitted_at = timezone.now()
            if new_status in ['in_progress'] and not self.processing_started_at:
                self.processing_started_at = timezone.now()
            if new_status in ['validated', 'rejected']:
                self.processed_at = timezone.now()
                if user:
                    self.validated_by = user
            if notes:
                if new_status == 'rejected':
                    self.rejection_reason = notes
                elif new_status == 'complement_requested':
                    self.complement_requested = notes
                else:
                    self.agent_notes = notes
            self.save()
            # Créer une entrée dans l'historique
            StatusHistory.objects.create(
                declaration=self,
                old_status=old_status,
                new_status=new_status,
                changed_by=user,
                notes=notes,
            )
            return True
        return False


class StatusHistory(models.Model):
    """Historique des changements de statut d'une déclaration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    declaration = models.ForeignKey(
        Declaration, on_delete=models.CASCADE, related_name='status_history'
    )
    old_status = models.CharField(_('Ancien statut'), max_length=30)
    new_status = models.CharField(_('Nouveau statut'), max_length=30)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(_('Date'), default=timezone.now)

    class Meta:
        verbose_name = _('Historique statut')
        verbose_name_plural = _('Historiques statuts')
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.declaration.declaration_number}: {self.old_status} → {self.new_status}'


class DocumentFound(models.Model):
    """Signalement qu'un document perdu a été retrouvé."""

    class FoundStatus(models.TextChoices):
        PENDING = 'pending', _('En attente de récupération')
        NOTIFIED = 'notified', _('Citoyen notifié')
        COLLECTED = 'collected', _('Document récupéré')
        UNCLAIMED = 'unclaimed', _('Non réclamé — archivé')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    declaration = models.OneToOneField(
        Declaration, on_delete=models.CASCADE,
        related_name='found_record', verbose_name=_('Déclaration')
    )
    found_by = models.CharField(_('Trouvé par'), max_length=200, blank=True,
        help_text=_('Nom de la personne ou institution ayant trouvé le document'))
    found_at = models.DateField(_('Date de découverte'), default=timezone.now)
    found_location = models.CharField(_('Lieu de découverte'), max_length=300, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    status = models.CharField(
        _('Statut'), max_length=20,
        choices=FoundStatus.choices, default=FoundStatus.PENDING
    )
    collection_deadline = models.DateField(_('Date limite de récupération'), null=True, blank=True)
    collected_at = models.DateTimeField(_('Récupéré le'), null=True, blank=True)
    notified_at = models.DateTimeField(_('Citoyen notifié le'), null=True, blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='found_documents',
        verbose_name=_('Enregistré par')
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _('Document retrouvé')
        verbose_name_plural = _('Documents retrouvés')
        ordering = ['-created_at']

    def __str__(self):
        return f'Retrouvé: {self.declaration.declaration_number} — {self.get_status_display()}'

    def mark_collected(self):
        self.status = self.FoundStatus.COLLECTED
        self.collected_at = timezone.now()
        self.save(update_fields=['status', 'collected_at'])

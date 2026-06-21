"""
PerteDocsTG - Modèles Comptes Utilisateurs
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class UserManager(BaseUserManager):
    """Manager personnalisé pour le modèle User."""

    def create_user(self, email: str, password: str = None, **extra_fields) -> 'User':
        if not email:
            raise ValueError(_('L\'adresse email est obligatoire.'))
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields) -> 'User':
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.SUPER_ADMIN)
        return self.create_user(email, password, **extra_fields)

    def citizens(self):
        return self.filter(role=User.Role.CITIZEN)

    def agents(self):
        return self.filter(role=User.Role.AGENT)

    def admins(self):
        return self.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN])


class User(AbstractBaseUser, PermissionsMixin):
    """Modèle utilisateur principal avec rôles."""

    class Role(models.TextChoices):
        CITIZEN = 'citizen', _('Citoyen')
        AGENT = 'agent', _('Agent Administratif')
        ADMIN = 'admin', _('Administrateur')
        SUPER_ADMIN = 'super_admin', _('Super Administrateur')

    class Gender(models.TextChoices):
        MALE = 'M', _('Masculin')
        FEMALE = 'F', _('Féminin')
        OTHER = 'O', _('Autre')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('Adresse email'), unique=True, db_index=True)
    phone = PhoneNumberField(_('Téléphone'), blank=True, null=True, unique=True)

    # Informations personnelles
    first_name = models.CharField(_('Prénom'), max_length=150)
    last_name = models.CharField(_('Nom'), max_length=150)
    date_of_birth = models.DateField(_('Date de naissance'), null=True, blank=True)
    gender = models.CharField(_('Genre'), max_length=1, choices=Gender.choices, blank=True)
    nationality = models.CharField(_('Nationalité'), max_length=100, default='Togolaise')

    # Adresse
    address = models.TextField(_('Adresse'), blank=True)
    city = models.CharField(_('Ville'), max_length=100, blank=True)
    prefecture = models.ForeignKey(
        'core.Prefecture', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users', verbose_name=_('Préfecture')
    )

    # Rôle et statut
    role = models.CharField(_('Rôle'), max_length=20, choices=Role.choices, default=Role.CITIZEN)
    is_active = models.BooleanField(_('Actif'), default=True)
    is_staff = models.BooleanField(_('Staff'), default=False)
    is_verified = models.BooleanField(_('Email vérifié'), default=False)
    is_phone_verified = models.BooleanField(_('Téléphone vérifié'), default=False)

    # Avatar
    avatar = models.ImageField(_('Avatar'), upload_to='avatars/', null=True, blank=True)

    # Préférences
    language = models.CharField(_('Langue'), max_length=10, default='fr')
    dark_mode = models.BooleanField(_('Mode sombre'), default=False)
    email_notifications = models.BooleanField(_('Notifications email'), default=True)
    sms_notifications = models.BooleanField(_('Notifications SMS'), default=True)

    # Sécurité
    two_factor_enabled = models.BooleanField(_('2FA activé'), default=False)
    last_login_ip = models.GenericIPAddressField(_('Dernière IP'), null=True, blank=True)
    failed_login_attempts = models.PositiveSmallIntegerField(_('Tentatives échouées'), default=0)
    locked_until = models.DateTimeField(_('Verrouillé jusqu\'au'), null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(_('Créé le'), default=timezone.now)
    updated_at = models.DateTimeField(_('Modifié le'), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f'{self.get_full_name()} <{self.email}>'

    def save(self, *args, **kwargs):
        # Seul le Super Administrateur a accès à l'interface technique Django (/admin/)
        if self.role == self.Role.SUPER_ADMIN:
            self.is_staff = True
        else:
            self.is_staff = False
        super().save(*args, **kwargs)

    def get_full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self) -> str:
        return self.first_name

    def get_dashboard_url(self) -> str:
        """Renvoie l'URL du tableau de bord approprié selon le rôle."""
        from django.urls import reverse
        if self.is_administrator:
            return reverse('dashboard:admin')
        if self.is_agent:
            return reverse('dashboard:agent_home')
        return reverse('dashboard:home')

    @property
    def is_citizen(self) -> bool:
        return self.role == self.Role.CITIZEN

    @property
    def is_agent(self) -> bool:
        return self.role == self.Role.AGENT

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def is_super_admin(self) -> bool:
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_administrator(self) -> bool:
        return self.role in [self.Role.ADMIN, self.Role.SUPER_ADMIN]

    @property
    def is_staff_member(self) -> bool:
        return self.is_agent or self.is_administrator

    @property
    def is_locked(self) -> bool:
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def lock_account(self, minutes: int = 30) -> None:
        from datetime import timedelta
        self.locked_until = timezone.now() + timedelta(minutes=minutes)
        self.save(update_fields=['locked_until'])

    def unlock_account(self) -> None:
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['locked_until', 'failed_login_attempts'])


class AgentProfile(models.Model):
    """Profil étendu pour les agents administratifs."""

    class AgentType(models.TextChoices):
        PREFECTURAL = 'prefectural', _('Agent Préfectoral')
        REGIONAL = 'regional', _('Agent Régional')
        NATIONAL = 'national', _('Agent National')

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    agent_id = models.CharField(_('ID Agent'), max_length=50, unique=True)
    agent_type = models.CharField(_('Type d\'agent'), max_length=20, choices=AgentType.choices)
    department = models.CharField(_('Département'), max_length=200)
    prefecture = models.ForeignKey(
        'core.Prefecture', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='agents', verbose_name=_('Préfecture')
    )
    region = models.ForeignKey(
        'core.Region', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='agents', verbose_name=_('Région')
    )
    is_active = models.BooleanField(_('Actif'), default=True)

    class Meta:
        verbose_name = _('Profil Agent')
        verbose_name_plural = _('Profils Agents')

    def __str__(self) -> str:
        return f'Agent {self.agent_id} - {self.user.get_full_name()}'

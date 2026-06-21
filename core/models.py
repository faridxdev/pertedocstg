"""
PerteDocsTG - Modèles Core : Géographie du Togo
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Region(models.Model):
    """Les 5 régions administratives du Togo."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Nom'), max_length=100, unique=True)
    code = models.CharField(_('Code'), max_length=10, unique=True)
    capital = models.CharField(_('Chef-lieu'), max_length=100)
    is_active = models.BooleanField(_('Active'), default=True)
    order = models.PositiveSmallIntegerField(_('Ordre'), default=0)

    class Meta:
        verbose_name = _('Région')
        verbose_name_plural = _('Régions')
        ordering = ['order', 'name']

    def __str__(self) -> str:
        return self.name


class Prefecture(models.Model):
    """Préfectures du Togo."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='prefectures')
    name = models.CharField(_('Nom'), max_length=100)
    code = models.CharField(_('Code'), max_length=10, unique=True)
    capital = models.CharField(_('Chef-lieu'), max_length=100)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Préfecture')
        verbose_name_plural = _('Préfectures')
        ordering = ['region__name', 'name']
        unique_together = ['region', 'name']

    def __str__(self) -> str:
        return f'{self.name} ({self.region.name})'


class Commune(models.Model):
    """Communes du Togo."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prefecture = models.ForeignKey(Prefecture, on_delete=models.CASCADE, related_name='communes')
    name = models.CharField(_('Nom'), max_length=100)
    code = models.CharField(_('Code'), max_length=20, unique=True)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Commune')
        verbose_name_plural = _('Communes')
        ordering = ['prefecture__name', 'name']

    def __str__(self) -> str:
        return f'{self.name} ({self.prefecture.name})'


class SiteConfiguration(models.Model):
    """Configuration globale du site (singleton)."""

    site_name = models.CharField(_('Nom du site'), max_length=100, default='PerteDocsTG')
    tagline = models.CharField(_('Accroche'), max_length=255, blank=True)
    contact_email = models.EmailField(_('Email contact'), blank=True)
    contact_phone = models.CharField(_('Téléphone contact'), max_length=20, blank=True)
    address = models.TextField(_('Adresse'), blank=True)
    maintenance_mode = models.BooleanField(_('Mode maintenance'), default=False)
    maintenance_message = models.TextField(_('Message maintenance'), blank=True)
    allow_registrations = models.BooleanField(_('Inscriptions ouvertes'), default=True)
    max_declarations_per_user = models.PositiveIntegerField(_('Max déclarations par utilisateur'), default=10)
    receipt_validity_days = models.PositiveIntegerField(_('Validité récépissé (jours)'), default=90)
    logo = models.ImageField(_('Logo'), upload_to='config/', null=True, blank=True)
    favicon = models.ImageField(_('Favicon'), upload_to='config/', null=True, blank=True)

    class Meta:
        verbose_name = _('Configuration du site')
        verbose_name_plural = _('Configuration du site')

    def __str__(self) -> str:
        return self.site_name

    def save(self, *args, **kwargs):
        # Singleton pattern
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls) -> 'SiteConfiguration':
        config, _ = cls.objects.get_or_create(pk=1)
        return config

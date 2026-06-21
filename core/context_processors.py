from django.conf import settings

def site_context(request):
    """Ajoute des variables globales au contexte des templates."""
    return {
        'APP_NAME': getattr(settings, 'APP_NAME', 'PerteDocsTG'),
        'APP_VERSION': getattr(settings, 'APP_VERSION', '1.0.0'),
        'SUPPORT_EMAIL': getattr(settings, 'SUPPORT_EMAIL', ''),
        'SUPPORT_PHONE': getattr(settings, 'SUPPORT_PHONE', ''),
        'DEBUG_MODE': settings.DEBUG,
        'USE_TAILWIND_CDN': getattr(settings, 'USE_TAILWIND_CDN', False),
    }
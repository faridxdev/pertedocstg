"""
PerteDocsTG - Configuration des URLs principales
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

admin.site.site_header = 'PerteDocsTG Administration'
admin.site.site_title = 'PerteDocsTG'
admin.site.index_title = 'Plateforme d\'Administration'

urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),

    # API
    path('api/', include('api.urls')),

    # API Schema / Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # i18n
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    # Authentification
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),

    # Core / Landing
    path('', include('core.urls')),

    # Déclarations
    path('declarations/', include('declarations.urls')),

    # Documents
    path('documents/', include('documents.urls')),

    # Dashboard
    path('dashboard/', include('dashboard.urls')),

    # Notifications
    path('notifications/', include('notifications.urls')),

    # Audit
    path('audit/', include('audit.urls')),

    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass

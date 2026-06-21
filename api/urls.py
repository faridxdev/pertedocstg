"""
PerteDocsTG - URLs API REST
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    DocumentTypeViewSet,
    DeclarationViewSet,
    NotificationViewSet,
    VerificationViewSet,
    StatisticsViewSet,
)

router = DefaultRouter()
router.register(r'document-types', DocumentTypeViewSet, basename='document-types')
router.register(r'declarations', DeclarationViewSet, basename='declarations')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'verification', VerificationViewSet, basename='verification')
router.register(r'statistics', StatisticsViewSet, basename='statistics')

urlpatterns = [
    # JWT Auth
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Router URLs
    path('', include(router.urls)),
]

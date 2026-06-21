from django.urls import path
from django.http import JsonResponse
from django.utils import timezone
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.LandingPageView.as_view(), name='home'),
    path('verification/<str:token>/', views.VerificationPublicView.as_view(), name='verification'),
    path('a-propos/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('mentions-legales/', views.LegalView.as_view(), name='legal'),
    path('maintenance/', views.MaintenanceView.as_view(), name='maintenance'),
    path('health/', lambda r: JsonResponse({'status':'ok','ts':timezone.now().isoformat()}), name='health'),
]

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.redirect_dashboard, name='home'),
    path('citoyen/', views.CitizenDashboardView.as_view(), name='citizen'),
    path('agent/', views.AgentDashboardView.as_view(), name='agent_home'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin'),
    path('api/stats/', views.api_dashboard_stats, name='api_stats'),
]

from django.urls import path
from . import views

app_name = 'declarations'

urlpatterns = [
    path('nouvelle/', views.DeclarationWizardView.as_view(), {'step': 1}, name='wizard'),
    path('nouvelle/etape/<int:step>/', views.DeclarationWizardView.as_view(), name='wizard'),
    path('', views.DeclarationListView.as_view(), name='list'),
    path('<uuid:pk>/', views.DeclarationDetailView.as_view(), name='detail'),
    path('<uuid:pk>/confirmation/', views.DeclarationConfirmationView.as_view(), name='confirmation'),
    path('<uuid:pk>/recepisse/', views.declaration_download_receipt, name='download_receipt'),
    # Nouvelles fonctionnalités
    path('<uuid:pk>/retrouve/', views.agent_mark_document_found, name='mark_found'),
    path('<uuid:pk>/recupere/', views.agent_mark_collected, name='mark_collected'),
    path('<uuid:pk>/prendre-en-charge/', views.agent_take_charge, name='take_charge'),
    path('<uuid:pk>/valider/', views.agent_validate, name='validate'),
    path('<uuid:pk>/rejeter/', views.agent_reject, name='reject'),
    path('<uuid:pk>/complement/', views.agent_request_complement, name='request_complement'),
    # AJAX
    path('ajax/search/', views.ajax_declaration_search, name='ajax_search'),
    path('ajax/prefectures/', views.ajax_get_prefectures, name='ajax_prefectures'),
]

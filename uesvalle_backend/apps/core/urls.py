"""
URL patterns para el módulo core (autenticación, health checks, etc.)
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Health check
    path('health/', views.health_check, name='health-check'),
    
    # Autenticación de colaboradores
    path('auth/login/', views.colaborador_login, name='colaborador-login'),
    path('auth/logout/', views.colaborador_logout, name='colaborador-logout'),
    path('auth/verify/', views.colaborador_verify, name='colaborador-verify'),
]

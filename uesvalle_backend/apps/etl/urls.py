"""
URL patterns para el módulo ETL.
Define las rutas de la API REST para el sistema ETL.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from apps.core import views as core_views

# Crear router para ViewSets
router = DefaultRouter()
router.register(r'runs', views.ETLRunViewSet, basename='etl-runs')
router.register(r'municipios', views.DimMunicipioViewSet, basename='municipios')
router.register(r'instituciones', views.FactInstitucionViewSet, basename='instituciones')

# URLs específicas
urlpatterns = [
    # Health check desde core
    path('health/', core_views.health_check, name='health-check'),
    
    # Nuevos endpoints simples para tests
    path('run/', views.etl_run, name='etl-run-simple'),
    path('status/', views.etl_status, name='etl-status-simple'),
    
    # Router URLs
    path('', include(router.urls)),
    
    # Control del ETL
    path('control/execute/', views.ETLControlView.as_view(), name='etl-execute'),
    path('control/status/', views.ETLStatusView.as_view(), name='etl-status'),
    
    # Métricas y calidad
    path('metrics/', views.ETLMetricsView.as_view(), name='etl-metrics'),
    path('quality/', views.ETLDataQualityView.as_view(), name='etl-quality'),
    
    # Health check alternativo aquí también
    path('health-alt/', views.HealthCheckView.as_view(), name='etl-health-alt'),
]

app_name = 'etl'

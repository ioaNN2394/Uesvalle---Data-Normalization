"""
URL patterns para el módulo ETL.
Define las rutas de la API REST para el sistema ETL.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Crear router para ViewSets
router = DefaultRouter()
router.register(r'runs', views.ETLRunViewSet, basename='etl-runs')
router.register(r'municipios', views.DimMunicipioViewSet, basename='municipios')
router.register(r'instituciones', views.FactInstitucionViewSet, basename='instituciones')

# URLs específicas
urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Control del ETL
    path('control/execute/', views.ETLControlView.as_view(), name='etl-execute'),
    path('control/status/', views.ETLStatusView.as_view(), name='etl-status'),
    
    # Health check
    path('health/', views.HealthCheckView.as_view(), name='etl-health'),
]

app_name = 'etl'

"""
URL patterns para el módulo ETL.

Rutas principales:
- /api/etl/jobs/              - Listar/crear jobs ETL
- /api/etl/jobs/:id/          - Detalles del job
- /api/etl/jobs/:id/cancel/   - Cancelar job
- /api/etl/jobs/:id/logs/     - Logs del job
- /api/etl/status/            - Estado general
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views_v2

# Router para ViewSet de Jobs
router = DefaultRouter()
router.register(r'jobs', views_v2.ETLJobViewSet, basename='etl-jobs')

# URLpatterns
urlpatterns = [
    path('', include(router.urls)),
    path('status/', views_v2.ETLJobViewSet.as_view({'get': 'status'}), name='etl-status'),
]

app_name = 'etl'


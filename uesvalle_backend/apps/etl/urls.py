"""
URL patterns para el módulo ETL.

Rutas principales:
- /api/etl/upload/           - POST para subir archivos Excel
- /api/etl/jobs/             - Listar/crear jobs ETL
- /api/etl/jobs/:id/         - Detalles del job
- /api/etl/jobs/:id/cancel/  - Cancelar job
- /api/etl/jobs/:id/logs/    - Logs del job
- /api/etl/status/           - Estado general
- /api/map/markers/          - GET marcadores para el mapa
- /api/map/institucion/<id>/ - GET detalles de institución
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views_v2
from .views import MapMarkersView, MapDetailsView, InstitutionSearchView

# Router para ViewSet de Jobs
router = DefaultRouter()
router.register(r'jobs', views_v2.ETLJobViewSet, basename='etl-jobs')

# URLpatterns
urlpatterns = [
    # Upload endpoint
    path('upload/', views_v2.upload_etl_file, name='etl-upload'),
    
    # Router endpoints
    path('', include(router.urls)),
    path('status/', views_v2.ETLJobViewSet.as_view({'get': 'status'}), name='etl-status'),
    
    # Map endpoints
    path('map/markers/', MapMarkersView.as_view(), name='map-markers'),
    path('map/institucion/<uuid:institucion_id>/', MapDetailsView.as_view(), name='map-details'),
    path('map/search/', InstitutionSearchView.as_view(), name='map-search'),
]

app_name = 'etl'


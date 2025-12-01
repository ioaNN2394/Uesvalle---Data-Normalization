"""
URL configuration for uesvalle_backend project.

Sistema ETL para normalización de datos educativos UESVALLE.
Integra MySQL + Excel → normaliza → carga en Supabase (Postgres).
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.conf.urls.static import static


@require_http_methods(["GET"])
def api_root(request):
    """Root endpoint de la API."""
    return JsonResponse({
        'message': 'API ETL UESVALLE - Sistema de Normalización de Datos Educativos',
        'version': '1.0.0',
        'endpoints': {
            'etl': '/api/etl/',
            'reports': '/api/reports/',
            'admin': '/admin/',
            'health': '/api/etl/health/',
            'docs': '/api/docs/' if hasattr(request, 'build_absolute_uri') else None
        }
    })


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Root
    path('api/', api_root, name='api-root'),

    # Core Module (auth, health)
    path('api/core/', include('apps.core.urls')),

    # ETL Module
    path('api/etl/', include('apps.etl.urls')),

    # Reports Module
    path('api/reports/', include('apps.reports.urls')),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
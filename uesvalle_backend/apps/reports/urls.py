"""
URL patterns para el módulo de reportes.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Listado de reportes disponibles
    path('', views.ReportListView.as_view(), name='report-list'),
    
    # Generar reporte con filtros (maneja GET para opciones y POST para generar)
    path('generate/', views.GenerateReportView.as_view(), name='generate-report'),
    
    # Búsqueda de instituciones
    path('instituciones/', views.InstitucionesSearchView.as_view(), name='instituciones-search'),
    
    # Verificar estado de una tarea de reporte
    path('status/<str:task_id>/', views.ReportStatusView.as_view(), name='report-status'),
    
    # Descargar un reporte generado
    path('download/<str:task_id>/<str:filename>/', views.DownloadReportView.as_view(), name='download-report'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]

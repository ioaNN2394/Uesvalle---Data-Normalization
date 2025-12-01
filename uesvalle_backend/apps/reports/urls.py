"""
URL patterns para el módulo de reportes.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Listado de reportes disponibles
    path('', views.ReportListView.as_view(), name='report-list'),
    
    # Generar reporte con filtros
    path('generate/', views.GenerateReportView.as_view(), name='generate-report'),
    
    # Obtener opciones de filtros (para el frontend)
    path('filter-options/', views.GenerateReportView.as_view(), name='filter-options'),
    
    # Verificar estado de una tarea de reporte
    path('status/<str:task_id>/', views.ReportStatusView.as_view(), name='report-status'),
    
    # Descargar un reporte generado
    path('download/<str:task_id>/<str:filename>/', views.DownloadReportView.as_view(), name='download-report'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]

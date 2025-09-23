"""
URL patterns para el módulo de reportes.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Endpoints básicos de reportes
    path('', views.ReportListView.as_view(), name='report-list'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('export/', views.ExportDataView.as_view(), name='export-data'),
]

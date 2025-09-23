"""
Vistas para el módulo de reportes.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


class ReportListView(APIView):
    """Vista para listar reportes disponibles."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Retorna lista de reportes disponibles."""
        reports = [
            {
                'id': 'instituciones',
                'name': 'Reporte de Instituciones',
                'description': 'Listado completo de instituciones educativas'
            },
            {
                'id': 'matricula',
                'name': 'Reporte de Matrícula',
                'description': 'Estadísticas de matrícula por periodo'
            },
            {
                'id': 'pae',
                'name': 'Reporte PAE',
                'description': 'Programa de Alimentación Escolar'
            }
        ]
        
        return Response({
            'reports': reports,
            'total': len(reports)
        })


class DashboardView(APIView):
    """Vista para datos del dashboard."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Retorna datos para el dashboard."""
        try:
            # Importar aquí para evitar imports circulares
            from apps.etl.models import Institucion, DimMunicipio
            
            dashboard_data = {
                'summary': {
                    'total_instituciones': Institucion.objects.count(),
                    'total_municipios': DimMunicipio.objects.count(),
                },
                'charts': {
                    'instituciones_por_estado': [],
                    'instituciones_por_municipio': []
                }
            }
            
            return Response(dashboard_data)
            
        except Exception as e:
            return Response({
                'error': 'Error obteniendo datos del dashboard',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExportDataView(APIView):
    """Vista para exportar datos."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Endpoint para exportar datos."""
        export_format = request.query_params.get('format', 'json')
        
        return Response({
            'message': f'Exportación en formato {export_format} no implementada aún',
            'available_formats': ['json', 'csv', 'excel']
        })

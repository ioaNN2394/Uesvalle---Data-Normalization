"""
Vistas de la API REST para el módulo ETL.
Proporciona endpoints para consultar estado y ejecutar el ETL.
"""
import os
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
import logging

from .models import (
    ETLRun, DimMunicipio, DimSede, FactInstitucion, 
    ChangeLog, StgInstitucionMySQL
)
from .serializers import (
    ETLRunSerializer, DimMunicipioSerializer, DimSedeSerializer,
    FactInstitucionSerializer, FactInstitucionListSerializer,
    FactInstitucionMapSerializer, ChangeLogSerializer,
    ETLTriggerSerializer, ETLStatusSerializer, InstitucionFilterSerializer
)
from .services import ETLOrchestrator

logger = logging.getLogger(__name__)


class ETLRunViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar ejecuciones del ETL."""
    
    queryset = ETLRun.objects.all().order_by('-started_at')
    serializer_class = ETLRunSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['started_at', 'finished_at', 'status']
    ordering = ['-started_at']
    
    @action(detail=True, methods=['get'])
    def change_logs(self, request, pk=None):
        """Obtiene los logs de cambios de una ejecución específica."""
        etl_run = self.get_object()
        logs = ChangeLog.objects.filter(etl_run=etl_run).order_by('-timestamp')
        
        # Paginación manual simple
        page_size = 100
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        logs_page = logs[start:end]
        serializer = ChangeLogSerializer(logs_page, many=True)
        
        return Response({
            'results': serializer.data,
            'count': logs.count(),
            'page': page,
            'total_pages': (logs.count() + page_size - 1) // page_size
        })


class DimMunicipioViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar municipios."""
    
    queryset = DimMunicipio.objects.all().order_by('departamento_nombre', 'nombre')
    serializer_class = DimMunicipioSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['departamento_codigo']
    search_fields = ['nombre', 'departamento_nombre']
    ordering_fields = ['nombre', 'departamento_nombre']
    
    @action(detail=False, methods=['get'])
    def by_departamento(self, request):
        """Agrupa municipios por departamento."""
        municipios = self.get_queryset()
        departamentos = {}
        
        for municipio in municipios:
            dept = municipio.departamento_nombre or 'Sin Departamento'
            if dept not in departamentos:
                departamentos[dept] = []
            
            departamentos[dept].append({
                'id': municipio.id,
                'codigo': municipio.codigo,
                'nombre': municipio.nombre
            })
        
        return Response(departamentos)


class FactInstitucionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar instituciones educativas."""
    
    queryset = FactInstitucion.objects.select_related('municipio').all()
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'sector', 'zona', 'municipio__codigo']
    search_fields = ['nombre', 'codigo_dane', 'municipio__nombre']
    ordering_fields = ['nombre', 'estado', 'municipio__nombre', 'created_at']
    ordering = ['nombre']
    
    def get_serializer_class(self):
        """Retorna serializer apropiado según la acción."""
        if self.action == 'list':
            return FactInstitucionListSerializer
        elif self.action == 'for_map':
            return FactInstitucionMapSerializer
        return FactInstitucionSerializer
    
    def get_queryset(self):
        """Aplica filtros dinámicos al queryset."""
        queryset = super().get_queryset()
        
        # Filtro por coordenadas (para mapa)
        has_coordinates = self.request.query_params.get('has_coordinates')
        if has_coordinates and has_coordinates.lower() == 'true':
            queryset = queryset.filter(
                latitud__isnull=False, 
                longitud__isnull=False
            )
        
        # Filtro por múltiples estados
        estados = self.request.query_params.getlist('estados[]')
        if estados:
            queryset = queryset.filter(estado__in=estados)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def for_map(self, request):
        """Endpoint optimizado para el mapa - solo datos esenciales."""
        queryset = self.get_queryset().filter(
            latitud__isnull=False, 
            longitud__isnull=False
        )
        
        # Aplicar filtros adicionales
        municipio = request.query_params.get('municipio')
        if municipio:
            queryset = queryset.filter(municipio__nombre__icontains=municipio)
        
        estado = request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Retorna estadísticas de las instituciones."""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'por_estado': dict(
                queryset.values_list('estado').annotate(Count('id'))
            ),
            'por_sector': dict(
                queryset.values_list('sector').annotate(Count('id'))
            ),
            'por_zona': dict(
                queryset.values_list('zona').annotate(Count('id'))
            ),
            'con_coordenadas': queryset.filter(
                latitud__isnull=False, longitud__isnull=False
            ).count(),
            'sin_coordenadas': queryset.filter(
                Q(latitud__isnull=True) | Q(longitud__isnull=True)
            ).count(),
            'por_fuente': dict(
                queryset.values_list('source_system').annotate(Count('id'))
            )
        }
        
        return Response(stats)


class ETLControlView(APIView):
    """Vista para controlar la ejecución del ETL."""
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Ejecuta el ETL de forma asíncrona."""
        serializer = ETLTriggerSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        
        # Validar archivos si se proporcionan
        excel_a_path = validated_data.get('excel_a_path')
        excel_b_path = validated_data.get('excel_b_path')
        
        if excel_a_path and not os.path.exists(excel_a_path):
            return Response(
                {'error': f'Archivo Excel A no encontrado: {excel_a_path}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if excel_b_path and not os.path.exists(excel_b_path):
            return Response(
                {'error': f'Archivo Excel B no encontrado: {excel_b_path}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verificar si hay un ETL ejecutándose
            running_etl = ETLRun.objects.filter(status='running').first()
            if running_etl:
                return Response(
                    {
                        'error': 'Ya hay un ETL ejecutándose',
                        'running_etl_id': running_etl.id,
                        'started_at': running_etl.started_at
                    },
                    status=status.HTTP_409_CONFLICT
                )
            
            # Ejecutar ETL
            orchestrator = ETLOrchestrator()
            etl_run = orchestrator.run_etl_pipeline(
                excel_a_path=excel_a_path,
                excel_b_path=excel_b_path
            )
            
            serializer = ETLRunSerializer(etl_run)
            return Response(
                {
                    'message': 'ETL iniciado exitosamente',
                    'etl_run': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error iniciando ETL: {e}")
            return Response(
                {'error': f'Error iniciando ETL: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ETLStatusView(APIView):
    """Vista para consultar el estado general del ETL."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Retorna estado y estadísticas del ETL."""
        try:
            # Estadísticas de ejecuciones ETL
            etl_runs = ETLRun.objects.all()
            last_run = etl_runs.order_by('-started_at').first()
            
            etl_stats = {
                'last_run': last_run,
                'total_runs': etl_runs.count(),
                'successful_runs': etl_runs.filter(status='success').count(),
                'failed_runs': etl_runs.filter(status='failed').count(),
                'running_runs': etl_runs.filter(status='running').count(),
            }
            
            # Estadísticas de datos
            instituciones = FactInstitucion.objects.all()
            municipios = DimMunicipio.objects.all()
            
            data_stats = {
                'total_instituciones': instituciones.count(),
                'total_municipios': municipios.count(),
                'instituciones_activas': instituciones.filter(estado='Activo').count(),
                'instituciones_inactivas': instituciones.filter(estado='Inactivo').count(),
                'instituciones_mysql': instituciones.filter(source_system='mysql').count(),
                'instituciones_excel_a': instituciones.filter(source_system='excel_a').count(),
                'instituciones_excel_b': instituciones.filter(source_system='excel_b').count(),
            }
            
            # Combinar estadísticas
            status_data = {**etl_stats, **data_stats}
            
            serializer = ETLStatusSerializer(status_data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error consultando estado ETL: {e}")
            return Response(
                {'error': f'Error consultando estado: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HealthCheckView(APIView):
    """Vista para verificar el estado de las conexiones."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Verifica conectividad con las bases de datos."""
        health_status = {
            'timestamp': timezone.now(),
            'status': 'healthy',
            'databases': {}
        }
        
        # Verificar conexión a Supabase (default)
        try:
            from django.db import connections
            default_conn = connections['default']
            default_conn.cursor()
            health_status['databases']['supabase'] = 'connected'
        except Exception as e:
            health_status['databases']['supabase'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Verificar conexión a MySQL
        try:
            mysql_conn = connections['source_mysql']
            mysql_conn.cursor()
            health_status['databases']['mysql'] = 'connected'
        except Exception as e:
            health_status['databases']['mysql'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Verificar modelo principal
        try:
            FactInstitucion.objects.count()
            health_status['models'] = 'accessible'
        except Exception as e:
            health_status['models'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        status_code = status.HTTP_200_OK if health_status['status'] == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_status, status=status_code)

"""
Vistas de la API REST para el módulo ETL.

Endpoints:
- POST /api/etl/jobs/ - Crear job desde archivos
- GET /api/etl/jobs/:id/ - Estado del job
- GET /api/etl/jobs/:id/logs/ - Logs del job
- POST /api/etl/jobs/:id/cancel/ - Cancelar job
- GET /api/etl/jobs/:id/download-error-report/ - Descargar reporte de errores
"""
import os
import logging
from datetime import timedelta

from django.db.models import Q, Count, F
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.files.storage import default_storage

from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    ETLRun, ETLFile, ETLError, ETLMetrics, DataQualityCheck, ChangeLog
)
from .serializers import (
    ETLRunSerializer, ETLFileSerializer, ETLErrorSerializer
)
from .tasks import etl_run_job, etl_cancel_job

logger = logging.getLogger('etl.api')


# Nuevas vistas para soportar los endpoints de tests
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def etl_run(request):
    """
    Endpoint para ejecutar el ETL
    Requiere autenticación
    """
    try:
        orch = ETLOrchestrator()
        etl_run = orch._create_etl_run()
        return Response(
            {"etl_run_id": str(etl_run.id)},
            status=status.HTTP_202_ACCEPTED
        )
    except Exception as e:
        logger.error(f"Error ejecutando ETL: {e}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def etl_status(request):
    """
    Endpoint para consultar el estado actual del ETL
    Acceso público
    """
    try:
        last = ETLRun.objects.order_by("-started_at").first()
        current_status = getattr(last, "status", "idle") if last else "idle"
        return Response(
            {"status": current_status},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Error consultando estado ETL: {e}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ETLRunViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar ejecuciones del ETL."""
    
    queryset = ETLRun.objects.all().order_by('-started_at')
    serializer_class = ETLRunSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['started_at', 'finished_at', 'status']
    ordering = ['-started_at']


class DimMunicipioViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar municipios."""
    
    queryset = DimMunicipio.objects.all().order_by('nombre')
    serializer_class = DimMunicipioSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['codigo_departamento']
    search_fields = ['nombre']
    ordering_fields = ['nombre', 'codigo_departamento']
    
    @action(detail=False, methods=['get'])
    def by_departamento(self, request):
        """Agrupa municipios por departamento."""
        municipios = self.get_queryset()
        departamentos = {}
        
        for municipio in municipios:
            dept = municipio.codigo_departamento or 'Sin Departamento'
            if dept not in departamentos:
                departamentos[dept] = []
            
            departamentos[dept].append({
                'codigo_municipio': municipio.codigo_municipio,
                'nombre': municipio.nombre
            })
        
        return Response(departamentos)


class FactInstitucionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar instituciones (uesvalle.institucion)."""
    
    queryset = Institucion.objects.select_related('codigo_municipio').all()
    serializer_class = InstitucionSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'codigo_municipio']
    search_fields = ['nombre', 'dane_ie_id', 'sed_ie_id', 'uesvalle_ie_id']
    ordering_fields = ['nombre', 'estado', 'created_at']
    ordering = ['nombre']
    
    def get_queryset(self):
        """Aplica filtros dinámicos al queryset."""
        queryset = super().get_queryset()
        
        # Filtro por múltiples estados
        estados = self.request.query_params.getlist('estados[]')
        if estados:
            queryset = queryset.filter(estado__in=estados)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Retorna estadísticas de las instituciones."""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'por_estado': dict(
                queryset.values_list('estado').annotate(Count('id')).filter(estado__isnull=False)
            ),
            'por_municipio': dict(
                queryset.values_list('codigo_municipio').annotate(Count('id')).filter(codigo_municipio__isnull=False)
            ),
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
            etl_run = orchestrator.execute_full_pipeline(
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
            instituciones = Institucion.objects.all()
            municipios = DimMunicipio.objects.all()
            
            data_stats = {
                'total_instituciones': instituciones.count(),
                'total_municipios': municipios.count(),
                'instituciones_con_dane': instituciones.filter(dane_ie_id__isnull=False).count(),
                'instituciones_con_sed': instituciones.filter(sed_ie_id__isnull=False).count(),
                'instituciones_con_uesvalle': instituciones.filter(uesvalle_ie_id__isnull=False).count(),
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
            # No marcar como unhealthy si MySQL falla (es opcional)
        
        # Verificar modelo principal
        try:
            Institucion.objects.count()
            health_status['models'] = 'accessible'
        except Exception as e:
            health_status['models'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        status_code = status.HTTP_200_OK if health_status['status'] == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_status, status=status_code)


class ETLMetricsView(APIView):
    """Vista para obtener métricas y estadísticas del ETL."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Estadísticas generales
            total_runs = ETLRun.objects.count()
            successful_runs = ETLRun.objects.filter(status='success').count()
            failed_runs = ETLRun.objects.filter(status='failed').count()
            running_jobs = ETLRun.objects.filter(status='running').count()
            
            # Última ejecución exitosa
            last_success = ETLRun.objects.filter(status='success').order_by('-finished_at').first()
            
            # Estadísticas de datos
            total_instituciones = Institucion.objects.count()
            total_municipios = DimMunicipio.objects.count()
            total_sedes = Sede.objects.count()
            
            # Calcular tasa de éxito
            success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
            
            metrics = {
                'etl_statistics': {
                    'total_runs': total_runs,
                    'successful_runs': successful_runs,
                    'failed_runs': failed_runs,
                    'running_jobs': running_jobs,
                    'success_rate': round(success_rate, 2)
                },
                'data_statistics': {
                    'total_instituciones': total_instituciones,
                    'total_municipios': total_municipios,
                    'total_sedes': total_sedes,
                },
                'last_successful_run': {
                    'id': last_success.id if last_success else None,
                    'finished_at': last_success.finished_at if last_success else None,
                    'duration': last_success.duration if last_success else None,
                    'records_processed': last_success.meta.get('total_records', 0) if last_success and last_success.meta else 0
                } if last_success else None,
                'system_status': {
                    'is_running': running_jobs > 0,
                    'last_activity': last_success.finished_at if last_success else None
                }
            }
            
            return Response(metrics)
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas ETL: {e}")
            return Response({
                'error': 'Error obteniendo métricas',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ETLDataQualityView(APIView):
    """Vista para consultar la calidad de los datos procesados."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            etl_run_id = request.query_params.get('etl_run')
            
            # Filtrar por ETL run específico si se proporciona
            quality_checks = DataQualityCheck.objects.all()
            if etl_run_id:
                quality_checks = quality_checks.filter(etl_run_id=etl_run_id)
            
            # Obtener los últimos controles de calidad
            recent_checks = quality_checks.order_by('-timestamp')[:50]
            
            # Calcular estadísticas generales
            total_checks = quality_checks.count()
            passed_checks = quality_checks.filter(status='passed').count()
            failed_checks = quality_checks.filter(status='failed').count()
            warning_checks = quality_checks.filter(status='warning').count()
            
            # Agrupar por tipo de check
            check_types_stats = {}
            for check_type, _ in DataQualityCheck.CHECK_TYPES:
                type_checks = quality_checks.filter(check_type=check_type)
                if type_checks.exists():
                    check_types_stats[check_type] = {
                        'total': type_checks.count(),
                        'passed': type_checks.filter(status='passed').count(),
                        'failed': type_checks.filter(status='failed').count(),
                        'warning': type_checks.filter(status='warning').count()
                    }
            
            return Response({
                'summary': {
                    'total_checks': total_checks,
                    'passed_checks': passed_checks,
                    'failed_checks': failed_checks,
                    'warning_checks': warning_checks,
                    'quality_score': (passed_checks / total_checks * 100) if total_checks > 0 else 100
                },
                'by_check_type': check_types_stats,
                'recent_checks': [
                    {
                        'id': check.id,
                        'check_type': check.check_type,
                        'check_name': check.check_name,
                        'status': check.status,
                        'table_name': check.table_name,
                        'records_checked': check.records_checked,
                        'records_failed': check.records_failed,
                        'success_rate': check.success_rate,
                        'timestamp': check.timestamp
                    } for check in recent_checks
                ]
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo calidad de datos: {e}")
            return Response({
                'error': 'Error obteniendo datos de calidad',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
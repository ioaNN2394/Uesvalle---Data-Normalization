"""
Vistas de la API REST para el módulo ETL - v2

Endpoints:
- POST /api/etl/jobs/ - Crear job desde archivos
- GET /api/etl/jobs/:id/ - Estado del job
- GET /api/etl/jobs/:id/logs/ - Logs del job
- POST /api/etl/jobs/:id/cancel/ - Cancelar job
- GET /api/etl/status/ - Estado del sistema ETL
"""
import logging
from datetime import timedelta

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Avg

from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import ETLRun, ETLFile
from .serializers import ETLRunSerializer
from .tasks import etl_run_job, etl_cancel_job

logger = logging.getLogger('etl.api')


class ETLJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar trabajos ETL.
    
    Acciones:
    - list: Listar todos los jobs
    - retrieve: Obtener detalles de un job
    - cancel: Cancelar un job en progreso
    - logs: Obtener logs de un job
    """
    
    queryset = ETLRun.objects.all().order_by('-started_at')
    serializer_class = ETLRunSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['started_at', 'finished_at']
    
    def create(self, request, *args, **kwargs):
        """
        POST /api/etl/jobs/
        
        Crea un nuevo job ETL.
        
        Body:
            {
                "file_ids": [1, 2],  # IDs de archivos ETLFile
                "dry_run": false,
                "cancel_on_error": true
            }
        
        Response (202 Accepted):
            {
                "id": 1,
                "status": "pending",
                "task_id": "celery-task-uuid",
                "created_at": "2024-01-15T10:00:00Z"
            }
        """
        try:
            file_ids = request.data.get('file_ids', [])
            dry_run = request.data.get('dry_run', False)
            cancel_on_error = request.data.get('cancel_on_error', True)
            
            # Validar archivos existen
            files = ETLFile.objects.filter(id__in=file_ids)
            if len(files) != len(file_ids):
                return Response(
                    {'error': 'Algunos archivos no existen'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear ETLRun
            etl_run = ETLRun.objects.create(
                status='pending',
                metadata={'dry_run': dry_run, 'cancel_on_error': cancel_on_error}
            )
            
            # Asignar archivos
            for file_obj in files:
                file_obj.etl_run = etl_run
                file_obj.save()
            
            # Encolar tarea Celery
            task = etl_run_job.delay(
                etl_run_id=etl_run.id,
                dry_run=dry_run,
                cancel_on_error=cancel_on_error
            )
            
            # Guardar task ID
            etl_run.metadata['task_id'] = task.id
            etl_run.status = 'queued'
            etl_run.save()
            
            logger.info(f"Job ETL {etl_run.id} encolado con task {task.id}")
            
            serializer = self.get_serializer(etl_run)
            return Response(
                serializer.data,
                status=status.HTTP_202_ACCEPTED
            )
            
        except Exception as e:
            logger.error(f"Error creando job ETL: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        POST /api/etl/jobs/:id/cancel/
        
        Cancela un job en progreso.
        """
        etl_run = self.get_object()
        
        if etl_run.status not in ['pending', 'queued', 'running']:
            return Response(
                {'error': f'No se puede cancelar un job con estado {etl_run.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Cancelar tarea Celery
            task_id = etl_run.metadata.get('task_id')
            if task_id:
                from uesvalle_backend.celery import app as celery_app
                celery_app.control.revoke(task_id, terminate=True)
            
            # Ejecutar tarea de cancelación
            etl_cancel_job.delay(etl_run.id)
            
            serializer = self.get_serializer(etl_run)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error cancelando job: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """
        GET /api/etl/jobs/:id/logs/
        
        Obtiene logs pagados de un job.
        
        Query params:
            - level: 'error', 'warning', 'info', 'debug' (default: todos)
            - page: Página de resultados (default: 1)
            - page_size: Registros por página (default: 50)
        """
        etl_run = self.get_object()
        
        # Nota: La funcionalidad de errors requiere el modelo ETLError
        # que no está en la estructura actual. Retornar lista vacía.
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        
        return Response({
            'count': 0,
            'total_pages': 0,
            'page': page,
            'page_size': page_size,
            'results': []
        })
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        GET /api/etl/status/
        
        Estado general del sistema ETL.
        """
        try:
            total_jobs = ETLRun.objects.count()
            running_jobs = ETLRun.objects.filter(status='running').count()
            success_jobs = ETLRun.objects.filter(status='success').count()
            failed_jobs = ETLRun.objects.filter(status='failed').count()
            
            # Última ejecución
            last_job = ETLRun.objects.order_by('-started_at').first()
            
            return Response({
                'total_jobs': total_jobs,
                'running_jobs': running_jobs,
                'success_jobs': success_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': (success_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                'last_job': {
                    'id': last_job.id if last_job else None,
                    'status': last_job.status if last_job else None,
                    'started_at': last_job.started_at if last_job else None
                }
            })
            
        except Exception as e:
            logger.error(f"Error consultando status: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


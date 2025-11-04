"""
Vistas de la API REST para el módulo ETL - v2

Endpoints:
- POST /api/etl/upload/ - Subir archivos Excel
- POST /api/etl/jobs/ - Crear job desde archivos
- GET /api/etl/jobs/:id/ - Estado del job
- GET /api/etl/jobs/:id/logs/ - Logs del job
- POST /api/etl/jobs/:id/cancel/ - Cancelar job
- GET /api/etl/status/ - Estado del sistema ETL
"""
import logging
import os
import hashlib
from datetime import timedelta

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Avg
from django.conf import settings

from rest_framework import status, viewsets, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend

from .models import ETLRun, ETLFile
from .serializers import ETLRunSerializer, ETLFileSerializer
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


@api_view(['POST'])
def upload_etl_file(request):
    """
    POST /api/etl/upload/
    
    Subir uno o múltiples archivos Excel para procesamiento ETL.
    
    Multipart form-data con campo 'file' o 'files[]'.
    
    Respuesta (200 OK):
        [
            {
                "id": 1,
                "filename": "instituciones.xlsx",
                "file_type": "excel",
                "file_size": 102400,
                "status": "pending",
                "uploaded_at": "2024-01-15T10:00:00Z"
            }
        ]
    
    Errores:
    - 400: Archivo inválido, sin archivo, tamaño excedido
    - 415: Content-Type no soportado (debe ser multipart/form-data)
    - 500: Error interno del servidor
    """
    try:
        # Validar que hay archivos
        files = request.FILES.getlist('file')
        if not files:
            logger.warning("Intento de upload sin archivos")
            return Response(
                {'error': 'No se proporcionaron archivos', 'detail': 'El campo "file" es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Recibidos {len(files)} archivo(s) para ETL")
        
        uploaded_files = []
        errors = []
        
        for file_obj in files:
            try:
                # Validar extensión
                allowed_ext = ['.xlsx', '.xls', '.csv']
                filename_lower = file_obj.name.lower()
                if not any(filename_lower.endswith(ext) for ext in allowed_ext):
                    error_msg = f"{file_obj.name}: extensión no permitida. Permitidas: {', '.join(allowed_ext)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue
                
                # Validar tamaño
                max_size = getattr(settings, 'ETL_MAX_FILE_SIZE', 50 * 1024 * 1024)
                if file_obj.size > max_size:
                    error_msg = f"{file_obj.name}: archivo demasiado grande ({file_obj.size / 1024 / 1024:.1f}MB, máx {max_size / 1024 / 1024:.1f}MB)"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue
                
                # Determinar tipo
                if filename_lower.endswith(('.xlsx', '.xls')):
                    file_type = 'excel'
                elif filename_lower.endswith('.csv'):
                    file_type = 'csv'
                else:
                    file_type = 'unknown'
                
                # Crear directorio si no existe
                upload_dir = getattr(settings, 'ETL_UPLOAD_DIR', os.path.join(settings.BASE_DIR, 'etl_uploads'))
                os.makedirs(upload_dir, exist_ok=True)
                
                # Generar nombre único (hash + nombre)
                file_hash = hashlib.md5(f"{file_obj.name}{timezone.now().isoformat()}".encode()).hexdigest()
                unique_filename = f"{file_hash}_{file_obj.name}"
                file_path = os.path.join(upload_dir, unique_filename)
                
                # Guardar archivo
                with open(file_path, 'wb+') as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)
                
                logger.info(f"Archivo guardado: {unique_filename} ({file_obj.size} bytes)")
                
                # Crear registro ETLFile
                etl_file = ETLFile.objects.create(
                    filename=file_obj.name,
                    file_type=file_type,
                    file_path=file_path,
                    file_size=file_obj.size,
                    status='pending'
                )
                
                logger.info(f"Registro ETLFile creado: id={etl_file.id}, status=pending")
                
                # Serializar respuesta
                serializer = ETLFileSerializer(etl_file)
                uploaded_files.append(serializer.data)
                
            except Exception as e:
                error_msg = f"Error procesando {file_obj.name}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
        
        # Responder
        if not uploaded_files and errors:
            return Response(
                {'error': 'Todos los archivos fueron rechazados', 'details': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_data = {
            'uploaded': uploaded_files,
            'failed': len(errors),
        }
        if errors:
            response_data['errors'] = errors
        
        logger.info(f"Upload completado: {len(uploaded_files)} exitosos, {len(errors)} fallidos")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error en endpoint upload: {e}", exc_info=True)
        return Response(
            {'error': 'Error interno del servidor', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

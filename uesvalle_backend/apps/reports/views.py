"""
Vistas para el módulo de reportes.
"""
import logging
import os
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from celery.result import AsyncResult
from django.conf import settings
from django.db import connection

from .report_generator import ReportFilter, StreamingReportGenerator
from .tasks import generate_excel_report, generate_pdf_report

logger = logging.getLogger(__name__)


class ReportListView(APIView):
    """Vista para listar reportes disponibles."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Retorna lista de reportes disponibles."""
        reports = [
            {
                'id': 'instituciones',
                'name': 'Reporte de Instituciones',
                'description': 'Listado completo de instituciones educativas con filtros',
                'formats': ['excel', 'pdf'],
                'filters': [
                    'municipios',
                    'conceptos_visita',
                    'anios',
                    'instituciones',
                    'estados',
                    'tiene_pae'
                ]
            }
        ]
        
        return Response({
            'reports': reports,
            'total': len(reports)
        })


class InstitucionesSearchView(APIView):
    """Vista para buscar instituciones por nombre, DANE o ID."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Retorna lista de instituciones que coinciden con la búsqueda.
        
        Query params:
            q: término de búsqueda (nombre, DANE, ID)
        """
        try:
            search_term = request.query_params.get('q', '').strip().lower()
            
            with connection.cursor() as cursor:
                if search_term:
                    # Búsqueda por nombre, DANE o ID (primeras letras)
                    query = """
                        SELECT DISTINCT
                            i.id,
                            i.nombre,
                            i.dane_ie_id
                        FROM "uesvalle"."institucion" i
                        WHERE 
                            LOWER(i.nombre) LIKE %s
                            OR LOWER(i.dane_ie_id) LIKE %s
                            OR LOWER(i.id::text) LIKE %s
                        ORDER BY i.nombre
                        LIMIT 20
                    """
                    search_pattern = f"%{search_term}%"
                    cursor.execute(query, [search_pattern, search_pattern, search_pattern])
                else:
                    # Sin búsqueda, retornar las primeras 20
                    query = """
                        SELECT DISTINCT
                            i.id,
                            i.nombre,
                            i.dane_ie_id
                        FROM "uesvalle"."institucion" i
                        ORDER BY i.nombre
                        LIMIT 20
                    """
                    cursor.execute(query)
                
                instituciones = [
                    {
                        'id': row[0],
                        'nombre': row[1],
                        'dane': row[2] or ''
                    }
                    for row in cursor.fetchall()
                ]
            
            return Response({
                'results': instituciones,
                'total': len(instituciones)
            })
        
        except Exception as e:
            logger.error(f"Error buscando instituciones: {str(e)}")
            return Response({
                'error': 'Error buscando instituciones',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateReportView(APIView):
    """Vista para generar reportes con filtros y obtener opciones de filtros."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Retorna información sobre los filtros disponibles."""
        try:
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Municipios
                cursor.execute("""
                    SELECT DISTINCT nombre
                    FROM "uesvalle"."dim_municipio"
                    ORDER BY nombre
                """)
                municipios = [
                    {'codigo': row[0], 'nombre': row[0]}
                    for row in cursor.fetchall()
                ]
                
                # Estados
                cursor.execute("""
                    SELECT DISTINCT estado
                    FROM "uesvalle"."institucion"
                    WHERE estado IS NOT NULL
                    ORDER BY estado
                """)
                estados = [row[0] for row in cursor.fetchall()]
            
            return Response({
                'filter_options': {
                    'municipios': municipios,
                    'conceptos_visita': [
                        {'value': 'F', 'label': 'Favorable'},
                        {'value': 'D', 'label': 'Desfavorable'},
                        {'value': 'FCR', 'label': 'Favorable con Requerimientos'}
                    ],
                    'estados': estados,
                    'tiene_pae': [
                        {'value': 'SI', 'label': 'Sí'},
                        {'value': 'NO', 'label': 'No'}
                    ]
                }
            })
        
        except Exception as e:
            logger.error(f"Error obteniendo opciones de filtros: {str(e)}")
            return Response({
                'error': 'Error obteniendo opciones de filtros',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """
        Genera un reporte con los filtros especificados.
        
        Body:
        {
            "format": "excel" | "pdf",
            "filters": {
                "municipios": ["nombre1", "nombre2"],
                "conceptos_visita": ["F", "D", "FCR"],
                "anios": [2023, 2024],
                "instituciones": ["nombre1", "nombre2"],
                "estados": ["ACTIVA", "CIERRE TEMPORAL"],
                "tiene_pae": true | false | null
            }
        }
        """
        try:
            output_format = request.data.get('format', 'excel').lower()
            filters_config = request.data.get('filters', {})
            
            # Validar formato
            if output_format not in ['excel', 'pdf']:
                return Response({
                    'error': 'Formato no válido. Debe ser "excel" o "pdf"'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Crear filtro desde configuración
            filters = ReportFilter(
                municipios=filters_config.get('municipios', []),
                conceptos_visita=filters_config.get('conceptos_visita', []),
                anios=filters_config.get('anios', []),
                instituciones=filters_config.get('instituciones', []),
                estados=filters_config.get('estados', []),
                tiene_pae=filters_config.get('tiene_pae')
            )
            
            # Obtener total de instituciones que coinciden
            generator = StreamingReportGenerator()
            total_instituciones = generator._get_total_instituciones(filters)
            
            # Validar que hay datos con los filtros especificados
            if filters.has_filters() and total_instituciones == 0:
                return Response({
                    'error': 'No se encontraron datos que coincidan con los filtros especificados. Por favor, verifica tus filtros.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Si no hay filtros y no hay confirmación, solicitar confirmación
            if not filters.has_filters() and not request.data.get('confirm', False):
                return Response({
                    'warning': f'No has seleccionado ningún filtro. Se generará un reporte de las {total_instituciones} instituciones. ¿Deseas continuar?',
                    'total_instituciones': total_instituciones,
                    'action_required': True
                }, status=status.HTTP_200_OK)
            
            # Crear tarea asíncrona
            if output_format == 'excel':
                task = generate_excel_report.delay(filters_config)
            else:
                task = generate_pdf_report.delay(filters_config)
            
            return Response({
                'task_id': task.id,
                'status': 'processing',
                'format': output_format,
                'message': 'Reporte en generación. Puedes verificar el estado con el task_id',
                'check_status_url': f'/api/reports/status/{task.id}/'
            }, status=status.HTTP_202_ACCEPTED)
        
        except Exception as e:
            logger.error(f"Error generando reporte: {str(e)}", exc_info=True)
            return Response({
                'error': 'Error al generar el reporte',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def options(self, request):
        """Retorna información sobre los filtros disponibles."""
        try:
            from apps.etl.models import Institucion
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Municipios
                cursor.execute("""
                    SELECT DISTINCT codigo_municipio, nombre
                    FROM "uesvalle"."dim_municipio"
                    ORDER BY nombre
                """)
                municipios = [
                    {'codigo': row[0], 'nombre': row[1]}
                    for row in cursor.fetchall()
                ]
                
                # Estados
                cursor.execute("""
                    SELECT DISTINCT estado
                    FROM "uesvalle"."institucion"
                    WHERE estado IS NOT NULL
                    ORDER BY estado
                """)
                estados = [row[0] for row in cursor.fetchall()]
                
                # Años
                cursor.execute("""
                    SELECT DISTINCT EXTRACT(YEAR FROM fechavisita) as anio
                    FROM "uesvalle"."visita"
                    WHERE fechavisita IS NOT NULL
                    ORDER BY anio DESC
                """)
                anios = [int(row[0]) for row in cursor.fetchall()]
            
            return Response({
                'filter_options': {
                    'municipios': municipios,
                    'conceptos_visita': [
                        {'value': 'F', 'label': 'Favorable'},
                        {'value': 'D', 'label': 'Desfavorable'},
                        {'value': 'FCR', 'label': 'Favorable con Requerimientos'}
                    ],
                    'anios': anios,
                    'estados': estados,
                    'tiene_pae': [
                        {'value': True, 'label': 'Con PAE'},
                        {'value': False, 'label': 'Sin PAE'},
                        {'value': None, 'label': 'Todos'}
                    ]
                }
            })
        
        except Exception as e:
            logger.error(f"Error obteniendo opciones de filtros: {str(e)}")
            return Response({
                'error': 'Error obteniendo opciones de filtros',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportStatusView(APIView):
    """Vista para verificar el estado de una tarea de reporte."""
    
    permission_classes = [AllowAny]
    
    def get(self, request, task_id):
        """
        Verifica el estado de una tarea y retorna el URL de descarga si está lista.
        
        Args:
            task_id: ID de la tarea Celery
        """
        try:
            task_result = AsyncResult(task_id)
            state = task_result.state
            
            logger.info(f"Verificando tarea {task_id}, estado: {state}")
            
            if state == 'PENDING':
                return Response({
                    'status': 'pending',
                    'task_id': task_id,
                    'message': 'La tarea aún no ha iniciado'
                })
            
            elif state == 'PROGRESS':
                info = task_result.info if isinstance(task_result.info, dict) else {}
                progress = info.get('progress', 0)
                return Response({
                    'status': 'processing',
                    'task_id': task_id,
                    'progress': progress,
                    'message': 'Generando reporte...'
                })
            
            elif state == 'SUCCESS':
                result = task_result.result
                logger.info(f"Tarea {task_id} completada. Resultado: {result}")
                
                if isinstance(result, dict) and result.get('success'):
                    return Response({
                        'status': 'success',
                        'task_id': task_id,
                        'download_url': result.get('download_url'),
                        'filename': result.get('filename'),
                        'format': result.get('format'),
                        'file_size': result.get('file_size'),
                        'created_at': result.get('created_at'),
                        'expires_at': result.get('expires_at')
                    })
                else:
                    error_msg = result.get('error', 'Error desconocido') if isinstance(result, dict) else str(result)
                    logger.error(f"Error en resultado de tarea {task_id}: {error_msg}")
                    return Response({
                        'status': 'error',
                        'task_id': task_id,
                        'error': error_msg
                    }, status=status.HTTP_200_OK)
            
            elif state == 'FAILURE':
                logger.error(f"Tarea {task_id} falló: {str(task_result.info)}")
                return Response({
                    'status': 'failed',
                    'task_id': task_id,
                    'error': str(task_result.info)
                }, status=status.HTTP_200_OK)
            
            else:
                logger.info(f"Tarea {task_id} en estado: {state}")
                return Response({
                    'status': state.lower(),
                    'task_id': task_id
                })
        
        except Exception as e:
            logger.error(f"Error verificando estado del reporte: {str(e)}", exc_info=True)
            # Retornar 200 en lugar de 500 para que el frontend pueda reintentar
            return Response({
                'error': 'Error verificando estado del reporte',
                'detail': str(e),
                'status': 'error'
            }, status=status.HTTP_200_OK)


class DownloadReportView(APIView):
    """Vista para descargar un reporte generado."""
    
    permission_classes = [AllowAny]
    
    def get(self, request, task_id, filename):
        """
        Descarga un archivo de reporte.
        
        Args:
            task_id: ID de la tarea Celery
            filename: Nombre del archivo a descargar
        """
        try:
            # Construir ruta segura del archivo
            file_path = os.path.join(
                settings.MEDIA_ROOT,
                'reports',
                task_id,
                filename
            )
            
            # Validar que el archivo existe y está dentro de la ruta permitida
            if not os.path.exists(file_path):
                return Response({
                    'error': 'Archivo no encontrado',
                    'detail': 'El reporte ha expirado o el archivo fue eliminado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validar que el archivo está dentro del directorio de reportes
            real_path = os.path.realpath(file_path)
            reports_dir = os.path.realpath(os.path.join(settings.MEDIA_ROOT, 'reports'))
            
            if not real_path.startswith(reports_dir):
                return Response({
                    'error': 'Acceso denegado',
                    'detail': 'No tienes permiso para acceder a este archivo'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Determinar tipo de contenido
            if filename.endswith('.xlsx'):
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif filename.endswith('.pdf'):
                content_type = 'application/pdf'
            else:
                content_type = 'application/octet-stream'
            
            # Retornar archivo
            response = FileResponse(
                open(file_path, 'rb'),
                as_attachment=True,
                filename=filename,
                content_type=content_type
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Error descargando reporte: {str(e)}")
            return Response({
                'error': 'Error descargando reporte',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

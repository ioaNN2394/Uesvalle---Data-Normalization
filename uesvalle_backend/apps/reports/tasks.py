"""
Tareas Celery para generación asíncrona de reportes.
Permite generar reportes grandes sin bloquear la API.
"""

import os
import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.db import transaction
from django.core.files.storage import default_storage
from django.conf import settings

from .report_generator import StreamingReportGenerator, ReportFilter

logger = logging.getLogger(__name__)


def _generate_report_task(task_self, filters_config: dict, output_format: str):
    """
    Función auxiliar para generar reportes en cualquier formato.
    
    Args:
        task_self: La instancia de la tarea (self)
        filters_config: Dict con configuración de filtros
        output_format: Formato ('excel' o 'pdf')
        
    Returns:
        dict: Información del reporte generado
    """
    try:
        task_id = task_self.request.id
        logger.info(f"Iniciando generación de {output_format} con task_id: {task_id}")
        logger.info(f"Configuración de filtros recibida: {filters_config}")
        
        # Crear filtro desde configuración
        filters = ReportFilter(
            municipios=filters_config.get('municipios', []),
            conceptos_visita=filters_config.get('conceptos_visita', []),
            anios=filters_config.get('anios', []),
            instituciones=filters_config.get('instituciones', []),
            estados=filters_config.get('estados', []),
            tiene_pae=filters_config.get('tiene_pae'),
            fecha_inicio=filters_config.get('fecha_inicio'),
            fecha_fin=filters_config.get('fecha_fin')
        )
        
        logger.info(f"Filtros procesados - fecha_inicio: {filters.fecha_inicio}, fecha_fin: {filters.fecha_fin}")
        
        # Generar nombre de archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = 'xlsx' if output_format == 'excel' else 'pdf'
        filename = f"reporte_{timestamp}.{ext}"
        
        # Obtener rutas
        task_manager = ReportGenerationTask()
        output_path = task_manager.get_report_path(task_id)
        
        # Generar reporte
        generator = StreamingReportGenerator()
        
        if output_format == 'excel':
            full_path = generator.generate_excel(filters, output_path, filename)
        elif output_format == 'pdf':
            full_path = generator.generate_pdf(filters, output_path, filename)
        else:
            raise ValueError(f"Formato no soportado: {output_format}")
        
        # Obtener tamaño del archivo
        file_size = os.path.getsize(full_path)
        
        logger.info(f"Reporte {output_format} generado exitosamente: {full_path} ({file_size} bytes)")
        
        return {
            'success': True,
            'task_id': task_id,
            'filename': filename,
            'format': output_format,
            'file_size': file_size,
            'download_url': task_manager.get_report_url(task_id, filename),
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error generando reporte {output_format}: {str(e)}", exc_info=True)
        
        return {
            'success': False,
            'error': str(e),
            'task_id': task_self.request.id
        }


class ReportGenerationTask:
    """Gestiona el estado y almacenamiento de tareas de generación de reportes."""
    
    def __init__(self):
        self.upload_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def get_report_path(self, task_id: str) -> str:
        """Obtiene la ruta donde guardar el reporte."""
        return os.path.join(self.upload_dir, task_id)
    
    def get_report_url(self, task_id: str, filename: str) -> str:
        """Obtiene la URL para descargar el reporte."""
        return f"/media/reports/{task_id}/{filename}"
    
    def cleanup_old_reports(self, hours: int = 24):
        """Elimina reportes más antiguos que X horas."""
        import shutil
        import time
        
        current_time = time.time()
        cutoff_time = current_time - (hours * 3600)
        
        for task_id in os.listdir(self.upload_dir):
            task_path = os.path.join(self.upload_dir, task_id)
            
            if os.path.isdir(task_path):
                modification_time = os.path.getmtime(task_path)
                
                if modification_time < cutoff_time:
                    try:
                        shutil.rmtree(task_path)
                        logger.info(f"Reporte antiguo eliminado: {task_id}")
                    except Exception as e:
                        logger.error(f"Error eliminando reporte: {task_id} - {str(e)}")


@shared_task(bind=True, name='reports.generate_excel_report')
def generate_excel_report(self, filters_config: dict):
    """
    Tarea Celery para generar reporte en Excel de forma asíncrona.
    
    Args:
        filters_config: Dict con configuración de filtros
        
    Returns:
        dict: Información del reporte generado
    """
    return _generate_report_task(self, filters_config, 'excel')


@shared_task(bind=True, name='reports.generate_pdf_report')
def generate_pdf_report(self, filters_config: dict):
    """
    Tarea Celery para generar reporte en PDF de forma asíncrona.
    
    Args:
        filters_config: Dict con configuración de filtros
        
    Returns:
        dict: Información del reporte generado
    """
    return _generate_report_task(self, filters_config, 'pdf')


@shared_task(name='reports.cleanup_old_reports')
def cleanup_old_reports():
    """
    Tarea periódica para limpiar reportes antiguos (más de 24 horas).
    Debe estar configurada en beat scheduler.
    """
    try:
        task_manager = ReportGenerationTask()
        task_manager.cleanup_old_reports(hours=24)
        logger.info("Limpieza de reportes antiguos completada")
        return {'success': True}
    except Exception as e:
        logger.error(f"Error en limpieza de reportes: {str(e)}")
        return {'success': False, 'error': str(e)}

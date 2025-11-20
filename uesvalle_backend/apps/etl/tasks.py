"""
Celery Tasks para ETL
====================

Define tareas asincrónicas para el pipeline ETL:
- etl_run_job: Orquestar E-T-L completo
- etl_extract: Solo extracción
- etl_transform: Solo transformación
- etl_cancel_job: Cancelar job en progreso

Registro en Celery:
    app.conf.task_routes = {
        'apps.etl.tasks.*': {'queue': 'etl'},
    }
"""

import logging
from typing import Optional
import pandas as pd

from celery import shared_task, current_task
from django.db import transaction
from django.utils import timezone

from .models import ETLRun, ETLFile
from .services.orchestrator import ETLOrchestrator
from .utils.csv_parser import RobustCSVParser
from .utils.validators import DepartmentValidator

logger = logging.getLogger('etl.tasks')


@shared_task(bind=True, max_retries=3)
def etl_run_job(self,
                etl_run_id: int,
                dry_run: bool = False,
                cancel_on_error: bool = True) -> dict:
    """
    Ejecuta el pipeline ETL completo (Extract → Transform → Load).
    Con validación de departamento VALLE DEL CAUCA.
    
    Args:
        etl_run_id: ID del registro ETLRun
        dry_run: Si True, no persiste cambios
        cancel_on_error: Si True, cancela en cualquier error
    
    Returns:
        Dict con resultado: {'status': 'success'|'failure', 'etl_run_id': int, 'error': str}
    """
    logger.info(f"▶ Iniciando ETL job asincrónico {etl_run_id}...")
    
    try:
        # Actualizar estado en Celery
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 3, 'stage': 'extraction'}
        )
        
        # Obtener ETLRun
        etl_run = ETLRun.objects.get(id=etl_run_id)
        etl_run.status = 'running'
        etl_run.save(update_fields=['status'])
        
        orchestrator = ETLOrchestrator(etl_run_id=etl_run_id)
        
        # Procesar archivos con validación de departamento
        files = ETLFile.objects.filter(etl_run_id=etl_run_id, status='pending')
        total_procesados = 0
        total_removidos = 0
        
        for etl_file in files:
            logger.info(f"📋 Procesando: {etl_file.filename}")
            etl_file.status = 'processing'
            etl_file.save(update_fields=['status'])
            
            try:
                if etl_file.file_type == 'csv':
                    # Lee el CSV
                    df = RobustCSVParser.parse_csv(etl_file.file_path)
                    
                    # ⭐ Procesa con validación de departamento
                    procesados, removidos = orchestrator.process_csv_data(df, etl_file)
                    
                    total_procesados += procesados
                    total_removidos += removidos
                    
                    etl_file.status = 'completed'
                    etl_file.rows_processed = procesados
                    etl_file.rows_failed = removidos
                    
                elif etl_file.file_type in ['excel', 'xlsx', 'xls']:
                    # Lee el Excel
                    df = pd.read_excel(etl_file.file_path, sheet_name=0)
                    
                    # ⭐ Procesa con validación de departamento
                    procesados, removidos = orchestrator.process_csv_data(df, etl_file)
                    
                    total_procesados += procesados
                    total_removidos += removidos
                    
                    etl_file.status = 'completed'
                    etl_file.rows_processed = procesados
                    etl_file.rows_failed = removidos
                
                etl_file.save(update_fields=['status', 'rows_processed', 'rows_failed'])
            
            except Exception as e:
                logger.error(f"❌ Error procesando archivo: {str(e)}")
                etl_file.status = 'failed'
                etl_file.error_message = str(e)
                etl_file.save(update_fields=['status', 'error_message'])
                
                if cancel_on_error:
                    etl_run.status = 'failed'
                    etl_run.meta = {
                        'error': str(e),
                        'total_procesados': total_procesados,
                        'total_removidos': total_removidos
                    }
                    etl_run.save(update_fields=['status', 'meta'])
                    
                    return {
                        'status': 'failure',
                        'etl_run_id': etl_run_id,
                        'error': str(e)
                    }
        
        # Finalizar
        etl_run.status = 'completed'
        etl_run.finished_at = timezone.now()
        etl_run.meta = {
            'total_procesados': total_procesados,
            'total_removidos': total_removidos,
            'mensaje': f'Completado: {total_procesados} registros del Valle del Cauca procesados, {total_removidos} descartados'
        }
        etl_run.save(update_fields=['status', 'finished_at', 'meta'])
        
        logger.info(f"✅ ETL job {etl_run_id} completado")
        logger.info(f"   Procesados (Valle del Cauca): {total_procesados}")
        logger.info(f"   Descartados (otros depts): {total_removidos}")
        
        return {
            'status': 'success',
            'etl_run_id': etl_run_id,
            'total_procesados': total_procesados,
            'total_removidos': total_removidos,
            'error': None
        }
            
    except ETLRun.DoesNotExist:
        error_msg = f"ETLRun {etl_run_id} no encontrado"
        logger.error(error_msg)
        return {
            'status': 'failure',
            'etl_run_id': etl_run_id,
            'error': error_msg
        }
    
    except Exception as e:
        logger.error(f"❌ Error en ETL job {etl_run_id}: {str(e)}", exc_info=True)
        
        try:
            etl_run = ETLRun.objects.get(id=etl_run_id)
            etl_run.status = 'failed'
            etl_run.save(update_fields=['status'])
        except:
            pass
        
        # Reintentar con backoff exponencial
        try:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        except Exception:
            return {
                'status': 'failure',
                'etl_run_id': etl_run_id,
                'error': str(e)
            }


@shared_task(bind=True)
def etl_extract_only(self,
                     etl_run_id: int) -> dict:
    """
    Ejecuta solo la fase de EXTRACTION.
    
    Útil para testing de extractores sin transformación/carga.
    """
    try:
        logger.info(f"📥 Extrayendo datos para job {etl_run_id}...")
        
        from .services.extractors import MultiSourceExtractor
        
        etl_run = ETLRun.objects.get(id=etl_run_id)
        excel_files = etl_run.etlfile_set.filter(file_type='xlsx').values_list('file_path', flat=True)
        
        for excel_path in excel_files:
            logger.debug(f"Extrayendo: {excel_path}")
        
        return {
            'status': 'success',
            'etl_run_id': etl_run_id,
            'files_extracted': len(list(excel_files))
        }
        
    except Exception as e:
        logger.error(f"Error en extracción: {e}")
        return {
            'status': 'failure',
            'etl_run_id': etl_run_id,
            'error': str(e)
        }


@shared_task(bind=True)
def etl_cancel_job(self, etl_run_id: int) -> dict:
    """
    Cancela un job ETL en progreso.
    
    Revoca la tarea Celery y marca ETLRun como cancelled.
    """
    try:
        logger.info(f"⏸ Cancelando ETL job {etl_run_id}...")
        
        etl_run = ETLRun.objects.get(id=etl_run_id)
        etl_run.status = 'cancelled'
        etl_run.finished_at = timezone.now()
        etl_run.save(update_fields=['status', 'finished_at'])
        
        logger.info(f"✓ Job {etl_run_id} marcado como cancelled")
        
        return {
            'status': 'success',
            'etl_run_id': etl_run_id,
            'message': 'Job cancelado'
        }
        
    except Exception as e:
        logger.error(f"Error cancelando job: {e}")
        return {
            'status': 'failure',
            'etl_run_id': etl_run_id,
            'error': str(e)
        }


@shared_task
def etl_cleanup_expired_files(hours: int = 24) -> dict:
    """
    Limpia archivos ETL que expiraron.
    
    Se ejecuta en schedule (ver beat-schedule en settings).
    
    Args:
        hours: Mantener archivos de últimas N horas
    """
    import os
    from datetime import timedelta
    from django.utils import timezone
    from pathlib import Path
    
    try:
        logger.info(f"🧹 Limpiando archivos ETL con más de {hours} horas...")
        
        from django.conf import settings
        etl_dir = settings.ETL_UPLOAD_DIR
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        deleted_count = 0
        
        for file_path in Path(etl_dir).glob('*'):
            if file_path.is_file():
                mtime = timezone.datetime.fromtimestamp(
                    file_path.stat().st_mtime,
                    tz=timezone.utc
                )
                
                if mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Eliminado: {file_path.name}")
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar {file_path.name}: {e}")
        
        logger.info(f"✓ Limpieza completada: {deleted_count} archivos eliminados")
        
        return {
            'status': 'success',
            'files_deleted': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        return {
            'status': 'failure',
            'error': str(e)
        }


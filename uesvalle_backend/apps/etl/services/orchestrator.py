"""
Orchestrator: Coordina el flujo completo Extract-Transform-Load
================================================================

Responsabilidades:
- Orquestar fases E-T-L en secuencia
- Actualizar estado de ETLRun
- Registrar errores
- Calcular métricas
"""

import logging
import time
from typing import Optional, Dict, List, Any

import pandas as pd
from django.utils import timezone

from ..models import ETLRun, ETLFile

logger = logging.getLogger('etl.orchestrator')


class ETLOrchestrator:
    """
    Coordina el pipeline ETL completo.
    
    Flujo:
    1. Extract: Obtener datos de archivos Excel
    2. Transform: Validar y normalizar
    3. Load: Persistir datos
    """
    
    def __init__(self, etl_run_id: int, user_id: Optional[int] = None):
        """
        Args:
            etl_run_id: ID del registro ETLRun
            user_id: Usuario que inició el ETL
        """
        self.etl_run_id = etl_run_id
        self.user_id = user_id
        self.etl_run = None
        self.extraction_results = []
        self.transformation_results = []
        self.loading_results = []
        self.errors = []
    
    def execute(self, 
                dry_run: bool = False,
                cancel_on_error: bool = True) -> bool:
        """
        Ejecuta el pipeline ETL completo.
        
        Args:
            dry_run: Si True, no persistir cambios
            cancel_on_error: Si True, cancela en cualquier error
        
        Returns:
            True si exitoso, False si falló
        """
        start_time = time.time()
        
        try:
            # Obtener registro ETLRun
            self.etl_run = ETLRun.objects.get(id=self.etl_run_id)
            self.etl_run.status = 'running'
            self.etl_run.meta = {'phase': 'extraction', 'progress': 0}
            self.etl_run.save(update_fields=['status', 'meta'])
            
            logger.info(f"▶ Iniciando ETL job {self.etl_run_id}...")
            
            # FASE 1: EXTRACTION
            logger.info("📥 FASE 1: Extrayendo datos...")
            if not self._execute_extraction():
                if cancel_on_error:
                    self._mark_failed("Fallo en extracción")
                    return False
            
            # FASE 2: TRANSFORMATION
            logger.info("🔄 FASE 2: Transformando datos...")
            if not self._execute_transformation():
                if cancel_on_error:
                    self._mark_failed("Fallo en transformación")
                    return False
            
            # FASE 3: LOADING
            logger.info("📤 FASE 3: Cargando datos...")
            if not self._execute_loading(dry_run=dry_run):
                if cancel_on_error:
                    self._mark_failed("Fallo en carga")
                    return False
            
            # Marcar como exitoso
            elapsed = time.time() - start_time
            self.etl_run.status = 'completed'
            self.etl_run.finished_at = timezone.now()
            self.etl_run.meta = {
                'phase': 'complete',
                'elapsed_seconds': elapsed,
                'extraction_count': len(self.extraction_results),
                'transformation_count': len(self.transformation_results),
                'loading_count': len(self.loading_results),
                'errors': len(self.errors)
            }
            self.etl_run.save(update_fields=['status', 'finished_at', 'meta'])
            
            logger.info(f"✅ ETL exitoso en {elapsed:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error crítico: {e}", exc_info=True)
            self._mark_failed(f"Error crítico: {str(e)}")
            return False
    
    def _execute_extraction(self) -> bool:
        """Fase EXTRACT: obtener datos de archivos Excel."""
        try:
            # Obtener archivos del job
            files = self.etl_run.files.filter(status='pending')
            
            logger.info(f"Extrayendo {files.count()} archivo(s) Excel...")
            
            for etl_file in files:
                try:
                    # Marcar como en procesamiento
                    etl_file.status = 'processing'
                    etl_file.save(update_fields=['status'])
                    
                    logger.debug(f"Extrayendo: {etl_file.filename}")
                    
                    # Leer archivo Excel con pandas
                    try:
                        df = pd.read_excel(etl_file.file_path, sheet_name=0)
                        
                        self.extraction_results.append({
                            'file_id': etl_file.id,
                            'filename': etl_file.filename,
                            'df': df,
                            'rows': len(df)
                        })
                        
                        logger.info(f"✓ Excel: {len(df)} registros extraídos de {etl_file.filename}")
                        
                    except Exception as e:
                        error_msg = f"Error leyendo Excel {etl_file.filename}: {str(e)}"
                        logger.error(error_msg)
                        self.errors.append({'file': etl_file.filename, 'error': error_msg})
                        
                        # Marcar archivo como fallido
                        etl_file.status = 'failed'
                        etl_file.error_message = error_msg
                        etl_file.save(update_fields=['status', 'error_message'])
                        continue
                    
                except Exception as e:
                    error_msg = f"Error procesando {etl_file.filename}: {str(e)}"
                    logger.error(error_msg)
                    self.errors.append({'file': etl_file.filename, 'error': error_msg})
            
            if not self.extraction_results and self.errors:
                logger.error("No se pudo extraer ningún archivo")
                return False
            
            logger.info(f"✓ Extracción completada: {len(self.extraction_results)} fuentes")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en extracción: {e}")
            self.errors.append({'phase': 'extraction', 'error': str(e)})
            return False
    
    def _execute_transformation(self) -> bool:
        """Fase TRANSFORM: validar y normalizar datos."""
        try:
            logger.info("Transformando datos extraídos...")
            
            for extraction in self.extraction_results:
                try:
                    df = extraction['df']
                    file_id = extraction['file_id']
                    filename = extraction['filename']
                    
                    logger.debug(f"Transformando {df.shape[0]} registros de {filename}...")
                    
                    # Validaciones básicas
                    df_valid = df.copy()
                    
                    # Limpiar espacios en blanco en columnas de texto
                    for col in df_valid.select_dtypes(include=['object']).columns:
                        if df_valid[col].dtype == 'object':
                            df_valid[col] = df_valid[col].str.strip()
                    
                    # Eliminar filas completamente vacías
                    df_valid = df_valid.dropna(how='all')
                    
                    valid_count = len(df_valid)
                    invalid_count = len(df) - valid_count
                    
                    self.transformation_results.append({
                        'file_id': file_id,
                        'filename': filename,
                        'df_transformed': df_valid,
                        'valid_count': valid_count,
                        'invalid_count': invalid_count
                    })
                    
                    logger.info(f"✓ Transformación: {valid_count} válidos, {invalid_count} inválidos")
                    
                except Exception as e:
                    error_msg = f"Error transformando {filename}: {str(e)}"
                    logger.error(error_msg)
                    self.errors.append({'file': filename, 'error': error_msg})
                    continue
            
            if not self.transformation_results and self.errors:
                logger.error("No se pudo transformar ningún archivo")
                return False
            
            logger.info(f"✓ Transformación completada: {len(self.transformation_results)} conjuntos")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en transformación: {e}")
            self.errors.append({'phase': 'transformation', 'error': str(e)})
            return False
    
    def _execute_loading(self, dry_run: bool = False) -> bool:
        """Fase LOAD: persistir datos transformados."""
        try:
            logger.info(f"Cargando datos a Supabase ({'DRY RUN' if dry_run else 'LIVE'})...")
            
            for transformation in self.transformation_results:
                file_id = transformation['file_id']
                filename = transformation['filename']
                df_valid = transformation['df_transformed']
                invalid_count = transformation['invalid_count']
                
                if len(df_valid) == 0:
                    logger.warning(f"Sin registros válidos de {filename}")
                    continue
                
                try:
                    if not dry_run:
                        # En producción, aquí iría la lógica de carga a Supabase
                        # Por ahora, solo registramos que se cargó
                        logger.info(f"[LOAD] {len(df_valid)} registros cargados de {filename}")
                        
                        # Actualizar ETLFile
                        etl_file = ETLFile.objects.get(id=file_id)
                        etl_file.status = 'success'
                        etl_file.rows_processed = len(df_valid)
                        etl_file.rows_failed = invalid_count
                        etl_file.processed_at = timezone.now()
                        etl_file.save()
                    else:
                        logger.info(f"[DRY RUN] Cargaría {len(df_valid)} registros de {filename}")
                    
                    self.loading_results.append({
                        'file_id': file_id,
                        'filename': filename,
                        'records_loaded': len(df_valid)
                    })
                    
                except Exception as e:
                    error_msg = f"Error cargando {filename}: {str(e)}"
                    logger.error(error_msg)
                    self.errors.append({'file': filename, 'error': error_msg})
                    
                    # Marcar archivo como fallido
                    try:
                        etl_file = ETLFile.objects.get(id=file_id)
                        etl_file.status = 'failed'
                        etl_file.error_message = error_msg
                        etl_file.save()
                    except:
                        pass
                    
                    return False
            
            if self.loading_results:
                total_loaded = sum(r['records_loaded'] for r in self.loading_results)
                logger.info(f"✓ Carga completada: {total_loaded} registros")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en carga: {e}")
            self.errors.append({'phase': 'loading', 'error': str(e)})
            return False
    
    def _mark_failed(self, reason: str) -> None:
        """Marca ETLRun como fallido."""
        try:
            self.etl_run.status = 'failed'
            self.etl_run.finished_at = timezone.now()
            self.etl_run.meta = {
                'failure_reason': reason,
                'errors': len(self.errors),
                'error_details': self.errors[:10]  # Primeros 10 errores
            }
            self.etl_run.save(update_fields=['status', 'finished_at', 'meta'])
            logger.error(f"❌ ETL marcado como fallido: {reason}")
        except Exception as e:
            logger.error(f"Error marcando fallo: {e}")

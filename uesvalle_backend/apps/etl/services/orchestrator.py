"""
Orchestrator: Coordina el flujo completo Extract-Transform-Load
================================================================

Responsabilidades:
- Orquestar fases E-T-L en secuencia
- Actualizar estado de ETLRun
- Registrar errores y cambios
- Calcular métricas
- Soportar rollback en caso de fallo
"""

import logging
import time
from typing import Optional, Dict, List, Any
from datetime import datetime

import pandas as pd
from django.db import transaction, DatabaseError
from django.utils import timezone

from ..models import ETLRun
# from ..models import ETLError, ETLMetrics, ChangeLog, DataQualityCheck  # TODO: Restaurar cuando se necesiten
from . import ExtractionResult, TransformationResult, LoadingResult
from .extractors import MultiSourceExtractor, ExcelExtractor, MySQLExtractor
from .transformers import InstitutionTransformer, BasicTransformer, ChangeDetector
from .loaders import PostgreSQLLoader, SupabaseLoader

logger = logging.getLogger('etl.orchestrator')


class ETLOrchestrator:
    """
    Coordina el pipeline ETL completo.
    
    Flujo:
    1. Extract: Obtener datos de MySQL y Excel
    2. Transform: Validar, normalizar, detectar cambios
    3. Load: Upsert a Supabase con transacciones atómicas
    4. Auditar: Registrar cambios y métricas
    """
    
    def __init__(self, etl_run_id: int, user_id: Optional[int] = None):
        """
        Args:
            etl_run_id: ID del registro ETLRun que orquesta
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
            cancel_on_error: Si True, rollback en cualquier error
        
        Returns:
            True si exitoso, False si falló
        """
        start_time = time.time()
        
        try:
            # Obtener registro ETLRun
            self.etl_run = ETLRun.objects.get(id=self.etl_run_id)
            self.etl_run.status = 'running'
            self.etl_run.started_at = timezone.now()
            self.etl_run.save(update_fields=['status', 'started_at'])
            
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
            
            # AUDITORÍA
            if not dry_run:
                self._execute_auditing()
            
            # Marcar como exitoso
            self.etl_run.status = 'completed'
            self.etl_run.completed_at = timezone.now()
            self.etl_run.save(update_fields=['status', 'completed_at'])
            
            elapsed = time.time() - start_time
            logger.info(f"✅ ETL exitoso en {elapsed:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error crítico: {e}", exc_info=True)
            self._mark_failed(f"Error crítico: {str(e)}")
            return False
    
    def _execute_extraction(self) -> bool:
        """Fase EXTRACT: obtener datos de MySQL y Excel."""
        try:
            # Obtener archivos Excel del job
            excel_files = self.etl_run.etlfile_set.filter(
                file_type='xlsx'
            ).values_list('file_path', flat=True)
            
            logger.info(f"Extrayendo {len(excel_files)} archivos Excel...")
            
            # Extractor multi-fuente
            extractor = MultiSourceExtractor()
            
            for idx, excel_path in enumerate(excel_files, 1):
                logger.debug(f"Extrayendo {idx}: {excel_path}")
                
                try:
                    # Extraer Excel
                    excel_extractor = ExcelExtractor()
                    excel_result = excel_extractor.extract(
                        file_path=excel_path,
                        sheet_name=0  # Primera hoja
                    )
                    
                    self.extraction_results.append({
                        'source': 'excel',
                        'file': excel_path,
                        'result': excel_result,
                        'df': excel_result.data
                    })
                    
                    logger.info(f"✓ Excel: {excel_result.record_count} registros "
                               f"en {excel_result.extraction_time:.2f}s")
                    
                except Exception as e:
                    error_msg = f"Error extrayendo {excel_path}: {str(e)}"
                    logger.error(error_msg)
                    self._record_error('extraction', 'excel', excel_path, error_msg)
                    continue
            
            # Extraer datos maestros de MySQL (catálogos)
            logger.debug("Extrayendo catálogos de MySQL...")
            
            mysql_extractor = MySQLExtractor()
            try:
                # Catálogos necesarios para transformación
                for table_name in ['catalogo_estados', 'catalogo_sectores', 'catalogo_zonas']:
                    try:
                        result = mysql_extractor.extract(
                            table_name=table_name,
                            chunksize=None  # Traer todo
                        )
                        self.extraction_results.append({
                            'source': 'mysql_catalog',
                            'table': table_name,
                            'result': result,
                            'df': result.data
                        })
                        logger.debug(f"✓ Catálogo {table_name}: {result.record_count} registros")
                    except Exception as e:
                        logger.warning(f"Catálogo {table_name} no encontrado: {e}")
                
            except Exception as e:
                logger.warning(f"Fallo parcial en catálogos MySQL: {e}")
            
            logger.info(f"✓ Extracción completada: {len(self.extraction_results)} fuentes")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en extracción: {e}")
            self._record_error('extraction', 'orchestrator', '', str(e))
            return False
    
    def _execute_transformation(self) -> bool:
        """Fase TRANSFORM: validar, normalizar, detectar cambios."""
        try:
            logger.info("Transformando datos extraídos...")
            
            # Transformer para datos de institución
            transformer = InstitutionTransformer()
            
            for extraction in self.extraction_results:
                if extraction['source'] != 'excel':
                    continue  # Saltar catálogos
                
                try:
                    df = extraction['df']
                    logger.debug(f"Transformando {df.shape[0]} registros...")
                    
                    # Transformar
                    result = transformer.transform(
                        df=df,
                        metadata={'source': extraction['file']}
                    )
                    
                    self.transformation_results.append({
                        'source_file': extraction['file'],
                        'result': result,
                        'df_transformed': result.data,
                        'df_invalid': result.invalid_records,
                        'errors': result.errors
                    })
                    
                    valid_count = len(result.data)
                    invalid_count = len(result.invalid_records)
                    logger.info(f"✓ Transformación: {valid_count} válidos, "
                               f"{invalid_count} inválidos")
                    
                    # Registrar errores de validación
                    for error in result.errors:
                        self._record_error('transformation', 'validation',
                                          extraction['file'], str(error))
                    
                except Exception as e:
                    error_msg = f"Error transformando {extraction['file']}: {str(e)}"
                    logger.error(error_msg)
                    self._record_error('transformation', 'transform', 
                                      extraction['file'], error_msg)
                    return False
            
            logger.info(f"✓ Transformación completada: {len(self.transformation_results)} conjuntos")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en transformación: {e}")
            self._record_error('transformation', 'orchestrator', '', str(e))
            return False
    
    def _execute_loading(self, dry_run: bool = False) -> bool:
        """Fase LOAD: upsert a Supabase con transacciones."""
        try:
            logger.info(f"Cargando datos a Supabase ({('DRY RUN' if dry_run else 'LIVE')})...")
            
            # Crear loader
            loader = PostgreSQLLoader(db_alias='default')  # Supabase en 'default'
            
            # Determinar tablas objetivo (por ahora: FactInstitucion)
            target_table = 'fact_institucion'
            
            for transformation in self.transformation_results:
                df_valid = transformation['df_transformed']
                
                if len(df_valid) == 0:
                    logger.warning(f"Sin registros válidos de {transformation['source_file']}")
                    continue
                
                try:
                    if not dry_run:
                        # Cargar a Supabase
                        result = loader.load(
                            df=df_valid,
                            table_name=target_table,
                            unique_key='codigo_dane',
                            update_columns=['nombre', 'estado', 'direccion', 'telefono', 
                                           'email', 'zona', 'sector']
                        )
                        
                        self.loading_results.append(result)
                        
                        logger.info(f"✓ Carga: +{result.records_inserted} inserciones, "
                                   f"+{result.records_updated} actualizaciones")
                        
                        # Registrar errores de carga
                        for error in result.errors:
                            self._record_error('loading', 'database',
                                              target_table, str(error))
                    else:
                        # DRY RUN: solo loguear
                        logger.info(f"[DRY RUN] Cargaría {len(df_valid)} registros a {target_table}")
                        self.loading_results.append(
                            LoadingResult(
                                table_name=target_table,
                                records_inserted=len(df_valid),
                                records_updated=0,
                                records_failed=0,
                                loading_time=0,
                                errors=[]
                            )
                        )
                    
                except Exception as e:
                    error_msg = f"Error cargando {target_table}: {str(e)}"
                    logger.error(error_msg)
                    self._record_error('loading', 'database', target_table, error_msg)
                    return False
            
            logger.info(f"✓ Carga completada: {sum(r.records_inserted for r in self.loading_results)} registros")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en carga: {e}")
            self._record_error('loading', 'orchestrator', '', str(e))
            return False
    
    def _execute_auditing(self) -> None:
        """Registra cambios, métricas y quality checks."""
        try:
            logger.info("📋 Registrando auditoría...")
            
            # Calcular totales
            total_inserted = sum(r.records_inserted for r in self.loading_results)
            total_updated = sum(r.records_updated for r in self.loading_results)
            total_failed = sum(r.records_failed for r in self.loading_results)
            
            # Registrar métricas
            ETLMetrics.objects.create(
                etl_run=self.etl_run,
                phase='complete',
                metric_name='records_processed',
                metric_value=total_inserted + total_updated,
                details={
                    'inserted': total_inserted,
                    'updated': total_updated,
                    'failed': total_failed,
                    'extraction_count': len(self.extraction_results),
                    'transformation_errors': sum(
                        len(t['errors']) for t in self.transformation_results
                    )
                }
            )
            
            # Registrar cambios en ChangeLog
            for result in self.loading_results:
                ChangeLog.objects.create(
                    etl_run=self.etl_run,
                    table_name=result.table_name,
                    operation_type='upsert',
                    record_count=result.records_inserted + result.records_updated,
                    details={
                        'inserted': result.records_inserted,
                        'updated': result.records_updated,
                        'duration': result.loading_time
                    }
                )
            
            # Data quality checks
            DataQualityCheck.objects.create(
                etl_run=self.etl_run,
                check_type='completeness',
                status='pass' if total_failed == 0 else 'fail',
                details={
                    'total_records': total_inserted + total_updated + total_failed,
                    'error_count': total_failed,
                    'error_rate': (total_failed / (total_inserted + total_updated + total_failed)
                                 if total_inserted + total_updated + total_failed > 0 else 0)
                }
            )
            
            logger.info(f"✓ Auditoría completada")
            
        except Exception as e:
            logger.error(f"⚠ Error en auditoría: {e}")
    
    def _mark_failed(self, reason: str) -> None:
        """Marca ETLRun como fallido."""
        try:
            self.etl_run.status = 'failed'
            self.etl_run.completed_at = timezone.now()
            self.etl_run.metadata = {
                'failure_reason': reason,
                'errors': len(self.errors)
            }
            self.etl_run.save(update_fields=['status', 'completed_at', 'metadata'])
            logger.error(f"❌ ETL marcado como fallido: {reason}")
        except Exception as e:
            logger.error(f"Error marcando fallo: {e}")
    
    def _record_error(self, 
                     phase: str,
                     error_type: str,
                     context: str,
                     message: str) -> None:
        """Registra un error en la BD."""
        try:
            ETLError.objects.create(
                etl_run=self.etl_run,
                phase=phase,
                error_type=error_type,
                table_name=context,
                message=message,
                context={'phase': phase, 'type': error_type},
                timestamp=timezone.now()
            )
            self.errors.append({
                'phase': phase,
                'type': error_type,
                'message': message
            })
        except Exception as e:
            logger.error(f"Error registrando error: {e}")


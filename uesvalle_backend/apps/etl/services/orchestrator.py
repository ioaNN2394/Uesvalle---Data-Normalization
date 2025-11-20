"""
Orchestrator: Coordina el flujo completo Extract-Transform-Load
================================================================

Responsabilidades:
- Orquestar fases E-T-L en secuencia
- Actualizar estado de ETLRun
- Registrar errores
- Calcular métricas
"""

import json
import logging
import time
import uuid
from typing import Optional, Dict, List, Any
import datetime

import pandas as pd
from django.utils import timezone
from django.db import connections
from django.conf import settings

from ..models import ETLRun, ETLFile, Institucion, Sede, Visita, FactMatricula, FactMatriculaEtnica
from ..utils.csv_parser import RobustCSVParser
from ..utils.normalizer import Normalizer
from ..utils.validators import DepartmentValidator
from ..utils.data_transformers import transformar_maestras_csv, transformar_visitas_mysql

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
        self.mapa_sedes_uuid = {}  # Mapeo dinámico entre código DANE y UUID de sedes
        self.dict_instituciones = {}
        self.dict_sedes = {}
        self.dict_instituciones_by_name = {}
    
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
        """Fase EXTRACT: obtener datos de archivos Excel/CSV."""
        try:
            # Obtener archivos del job
            files = ETLFile.objects.filter(etl_run_id=self.etl_run.id, status='pending')
            
            logger.info(f"Extrayendo {files.count()} archivo(s) (Excel/CSV)...")
            
            for etl_file in files:
                try:
                    # Marcar como en procesamiento
                    etl_file.status = 'processing'
                    etl_file.save(update_fields=['status'])
                    
                    logger.debug(f"Extrayendo: {etl_file.filename} (tipo: {etl_file.file_type})")
                    
                    # Leer archivo según tipo (Excel o CSV)
                    try:
                        if etl_file.file_type == 'csv':
                            # Usar RobustCSVParser para manejar delimitadores correctamente
                            df = RobustCSVParser.parse_csv(etl_file.file_path, delimiter=';', encoding='utf-8')
                            
                            # Validar coordenadas
                            valid, invalid, samples = RobustCSVParser.validate_coordinates(
                                df, lon_col='LONGITUD', lat_col='LATITUD'
                            )
                            
                            if valid == 0 and invalid > 0:
                                logger.warning(f"⚠️ No se detectaron coordenadas válidas en {etl_file.filename}")
                            else:
                                logger.info(f"✅ Coordenadas preservadas: {valid}/{valid+invalid} válidas")
                                
                            file_type_label = 'CSV'
                        else:  # excel, xlsx, xls
                            df = pd.read_excel(etl_file.file_path, sheet_name=0)
                            file_type_label = 'Excel'
                        
                        self.extraction_results.append({
                            'file_id': etl_file.id,
                            'filename': etl_file.filename,
                            'df': df,
                            'rows': len(df)
                        })
                        
                        logger.info(f"✓ {file_type_label}: {len(df)} registros extraídos de {etl_file.filename}")
                        
                    except Exception as e:
                        error_msg = f"Error leyendo {etl_file.file_type} {etl_file.filename}: {str(e)}"
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
            
            # EXTRACTION FROM MYSQL (Direct Connection)
            # Si está configurado en settings, intentamos extraer automáticamente
            if 'source_mysql' in settings.DATABASES:
                self._extract_from_mysql_db()
            
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
                    
                    # Normalizar coordenadas y fechas usando Normalizer
                    df_valid = Normalizer.normalize_coordinates(df_valid)
                    df_valid = Normalizer.normalize_dates(df_valid)
                    
                    # Limpiar espacios en blanco en columnas de texto
                    for col in df_valid.select_dtypes(include=['object']).columns:
                        if df_valid[col].dtype == 'object':
                            df_valid[col] = df_valid[col].str.strip()
                            
                    # Normalización específica de columnas DANE (FASE 0)
                    # Buscar columnas que parezcan códigos DANE
                    dane_cols = [c for c in df_valid.columns if 'DANE' in c.upper() or 'CODIGO' in c.upper()]
                    for col in dane_cols:
                        # Convertir a string, quitar decimales .0 si existen, quitar espacios
                        df_valid[col] = df_valid[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    
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
        """Carga datos usando transformadores externos."""
        try:
            logger.info(f"Cargando datos a BD ({'DRY RUN' if dry_run else 'LIVE'})...")
            self._load_dictionaries()
            
            # Clasificar y ordenar archivos para asegurar orden correcto (Sedes antes que Visitas)
            files_to_process = []
            for transformation in self.transformation_results:
                filename = transformation['filename']
                # Simple classification for sorting
                priority = 99
                if 'SEDE' in filename.upper() or 'SED' in filename.upper():
                    priority = 1
                elif 'VISITA' in filename.upper():
                    priority = 2
                
                files_to_process.append({**transformation, 'priority': priority})
            
            files_to_process.sort(key=lambda x: x['priority'])
            
            for transformation in files_to_process:
                df = transformation['df_transformed']
                filename = transformation['filename']
                file_id = transformation['file_id']
                
                logger.info(f"Procesando {filename}...")
                
                try:
                    # ⭐ USA LAS FUNCIONES EXTERNAS
                    if 'SEDE' in filename.upper() or 'SED' in filename.upper():
                        from apps.etl.utils.data_transformers import transformar_maestras_csv
                        
                        # Transforma usando función externa
                        df_inst, df_sedes, mapa = transformar_maestras_csv(df)
                        
                        # Inserta
                        inst_count = self._insert_instituciones(df_inst)
                        sedes_count = self._insert_sedes(df_sedes)
                        
                        logger.info(f"✓ Cargadas {inst_count} instituciones, {sedes_count} sedes")
                        
                        # Recarga diccionarios
                        self._load_dictionaries()
                        
                        if file_id:
                            ETLFile.objects.filter(id=file_id).update(
                                status='completed',
                                rows_processed=inst_count + sedes_count,
                                processed_at=timezone.now()
                            )
                    
                    elif 'VISITA' in filename.upper():
                        from apps.etl.utils.data_transformers import transformar_visitas_mysql
                        
                        df_visitas = transformar_visitas_mysql(df, self.dict_sedes)
                        visitas_count = self._insert_visitas(df_visitas)
                        
                        logger.info(f"✓ Cargadas {visitas_count} visitas")
                        
                        if file_id:
                            ETLFile.objects.filter(id=file_id).update(
                                status='completed',
                                rows_processed=visitas_count,
                                processed_at=timezone.now()
                            )
                
                except Exception as e:
                    logger.error(f"Error cargando {filename}: {str(e)}")
                    if file_id:
                        ETLFile.objects.filter(id=file_id).update(
                            status='failed',
                            error_message=str(e)
                        )
            
            return True
        
        except Exception as e:
            logger.error(f"Error en carga: {str(e)}")
            return False


    def _load_dictionaries(self):
        """Carga diccionarios de mapeo DANE -> UUID."""
        self.dict_instituciones = {
            inst.dane_ie_id: str(inst.id) 
            for inst in Institucion.objects.filter(dane_ie_id__isnull=False)
        }
        self.dict_sedes = {
            sede.dane_sede_id: str(sede.id) 
            for sede in Sede.objects.filter(dane_sede_id__isnull=False)
        }
        self.dict_instituciones_by_name = {
            inst.nombre: str(inst.id) 
            for inst in Institucion.objects.all()
        }
        logger.info(f"Diccionarios cargados: {len(self.dict_instituciones)} IEs, {len(self.dict_sedes)} Sedes")

    def _classify_file_content(self, df: pd.DataFrame, filename: str = '') -> str:
        """Clasifica el tipo de archivo basado en contenido y nombre."""
        cols = [c.upper() for c in df.columns]
        filename_upper = filename.upper()
        
        # Prioridad 1: Detectar por nombre de archivo
        if 'SEDE' in filename_upper and ('SISE' in filename_upper or 'SED' in filename_upper):
            return 'master_csv'
        if 'INSTITUCION' in filename_upper or 'INSTITUTION' in filename_upper:
            return 'master_csv'
        
        # Prioridad 2: Detectar por columnas
        if 'NOMBRE_INSTITUCION' in cols and ('COD_DANE' in cols or 'CODIGO_DANE' in cols):
            return 'master_csv'
        if 'SEDE_PRINCIPAL' in cols and 'COD_SEDE_PRINCIPAL' in cols:
            return 'master_csv'
        if 'FECHAVISITA' in cols or 'CONCEPTOVISITA' in cols or 'FECHA_VISITA' in cols:
            return 'visita'
        if any('MATRICULA' in c for c in cols):
            return 'matricula'
        if 'INDÍGENA' in cols or 'NARP' in cols or 'ROM' in cols or 'INDIGENA' in cols:
            return 'etnia'
        
        logger.warning(f"No se pudo clasificar {filename}. Columnas detectadas: {cols[:5]}...")
        return 'unknown'

    def _process_instituciones(self, df: pd.DataFrame):
        """DEPRECATED: Usar transformar_maestras_csv y _insert_instituciones."""
        pass

    def _process_sedes(self, df: pd.DataFrame) -> int:
        """DEPRECATED: Usar transformar_maestras_csv y _insert_sedes."""
        return 0

    def _process_visitas(self, df: pd.DataFrame) -> int:
        """Paso 2.1: Cargar Visitas (MySQL)."""
        logger.info(f"Procesando Visitas (Normalizando {len(df)} registros contra {len(self.dict_sedes)} sedes)...")
        
        if len(df) == 0:
            logger.warning("No hay registros de visitas para procesar")
            return 0
        
        if len(self.dict_sedes) == 0:
            logger.warning("No hay sedes cargadas aún, no se pueden procesar visitas")
            return 0
        
        # Primero normalizar todas las columnas a string para evitar errores con .str accessor
        try:
            df = Normalizer.normalize_all_strings(df)
            logger.debug("Columnas normalizadas a string")
        except Exception as e:
            logger.error(f"Error normalizando strings en visitas: {str(e)}", exc_info=True)
            return 0
        
        # Normalizar columnas
        df.columns = [c.lower() for c in df.columns]
        logger.debug(f"Columnas disponibles en visitas: {list(df.columns)}")
        
        cols_destino = ['fechavisita', 'conceptovisita', 'observacion']
        cols_extra = [c for c in df.columns if c not in cols_destino and c != 'codigodanesede']
        
        count = 0
        count_failed = 0
        
        for idx, row in df.iterrows():
            try:
                dane = str(row.get('codigodanesede', '')).strip() if 'codigodanesede' in df.columns else ''
                
                if not dane:
                    logger.debug(f"Fila {idx}: Sin DANE de sede, saltando")
                    count_failed += 1
                    continue
                
                sede_uuid = self.dict_sedes.get(dane)
                
                if not sede_uuid:
                    # logger.debug(f"Sede no encontrada para visita: {dane}")
                    count_failed += 1
                    continue
                
                # Empaquetar metadata
                meta_dict = {}
                for col in cols_extra:
                    if col in df.columns and pd.notnull(row[col]):
                        val = row[col]
                        # Convertir tipos no serializables
                        if isinstance(val, (pd.Timestamp, datetime.date)):
                            val = str(val)
                        meta_dict[col] = val
                
                try:
                    Visita.objects.create(
                        sede_id=sede_uuid,
                        fecha=row.get('fechavisita') if 'fechavisita' in df.columns else None,
                        resultado=row.get('conceptovisita') if 'conceptovisita' in df.columns else None,
                        observaciones=row.get('observacion') if 'observacion' in df.columns else None,
                        metadata=meta_dict
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Error creando visita en fila {idx} para sede {dane}: {str(e)}")
                    count_failed += 1
                    continue
                    
            except Exception as e:
                logger.error(f"Error procesando fila {idx} de visitas: {str(e)}", exc_info=True)
                count_failed += 1
                continue
        
        logger.info(f"✓ Visitas procesadas: {count} cargadas, {count_failed} fallidas")
        return count

    def _process_matricula(self, df: pd.DataFrame) -> int:
        """Paso 3.1: Cargar Matrícula (Totales)."""
        logger.info("Procesando Matrícula...")
        # Buscar columna de matrícula
        col_matricula = next((c for c in df.columns if 'MATRICULA' in c.upper()), None)
        col_dane = next((c for c in df.columns if 'DANE' in c.upper()), None)
        
        if not col_matricula or not col_dane:
            logger.error("Columnas requeridas no encontradas en archivo de matrícula")
            return 0
            
        count = 0
        for _, row in df.iterrows():
            dane = str(row[col_dane]).strip()
            sede_uuid = self.dict_sedes.get(dane)
            
            if not sede_uuid:
                continue
                
            FactMatricula.objects.update_or_create(
                sede_id=sede_uuid,
                corte_fecha='2024-12-01', # Hardcoded según manual
                defaults={
                    'total_alumnos': row[col_matricula],
                    'fuente': 'Excel Diciembre',
                    'metadata': {'origen': 'excel_matricula'}
                }
            )
            count += 1
        return count

    def _process_etnia(self, df: pd.DataFrame) -> int:
        """Paso 3.2: Cargar Matrícula Étnica (Unpivot)."""
        logger.info("Procesando Matrícula Étnica...")
        
        col_dane = next((c for c in df.columns if 'DANE' in c.upper()), None)
        if not col_dane:
            return 0
            
        # Identificar columnas de etnia
        etnia_cols = [c for c in df.columns if c.upper() in ['INDÍGENA', 'INDIGENA', 'NARP', 'ROM']]
        
        # Melt
        df_melted = df.melt(
            id_vars=[col_dane],
            value_vars=etnia_cols,
            var_name='grupo_etnico',
            value_name='total_alumnos'
        )
        
        count = 0
        for _, row in df_melted.iterrows():
            dane = str(row[col_dane]).strip()
            sede_uuid = self.dict_sedes.get(dane)
            
            if not sede_uuid:
                continue
                
            FactMatriculaEtnica.objects.update_or_create(
                sede_id=sede_uuid,
                corte_fecha='2025-02-13', # Hardcoded según manual
                grupo_etnico=row['grupo_etnico'].upper(),
                defaults={
                    'total_alumnos': row['total_alumnos'],
                    'fuente': 'Reporte Excel Feb 2025'
                }
            )
            count += 1
        return count
    
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
    
    def _extract_from_mysql_db(self):
        """Intenta extraer datos directamente de la BD MySQL configurada."""
        try:
            logger.info("Intentando extraer datos directamente de MySQL (source_mysql)...")
            
            if 'source_mysql' not in connections:
                logger.warning("Conexión 'source_mysql' no configurada")
                return
            
            conn = connections['source_mysql']
            
            # 1. Buscar tabla candidata
            # Prioridad 1: Tabla específica solicitada por usuario
            target_table = 'visitas_instituciones_educativos'
            table_name = None
            
            try:
                with conn.cursor() as cursor:
                    # Verificar si existe la tabla objetivo
                    cursor.execute(f"SHOW TABLES LIKE '{target_table}'")
                    if cursor.fetchone():
                        table_name = target_table
                        logger.info(f"Tabla {target_table} encontrada")
                    else:
                        logger.debug(f"Tabla {target_table} no existe, buscando alternativa...")
                        # Prioridad 2: Buscar por columna característica
                        cursor.execute("""
                            SELECT TABLE_NAME 
                            FROM INFORMATION_SCHEMA.COLUMNS 
                            WHERE COLUMN_NAME = 'fechavisita' 
                            AND TABLE_SCHEMA = DATABASE()
                            LIMIT 1
                        """)
                        row = cursor.fetchone()
                        if row:
                            table_name = row[0]
                            logger.info(f"Tabla alternativa encontrada: {table_name}")
            except Exception as e:
                logger.error(f"Error buscando tabla en MySQL: {str(e)}")
                return
            
            if not table_name:
                logger.warning("No se encontró ninguna tabla válida en MySQL (ni 'visitas_instituciones_educativos' ni con columna 'fechavisita').")
                return

            logger.info(f"Tabla de visitas encontrada en MySQL: {table_name}")
            
            # 2. Leer datos usando pandas
            try:
                # Asegurar conexión subyacente
                if conn.connection is None:
                    conn.connect()
                
                # Usamos la conexión DBAPI raw de Django
                logger.debug(f"Leyendo SELECT * FROM `{table_name}`...")
                df = pd.read_sql(f"SELECT * FROM `{table_name}`", conn.connection)
                
                logger.info(f"✓ MySQL: {len(df)} registros extraídos de {table_name}")
                logger.debug(f"  Columnas: {list(df.columns)}")
                
                if len(df) > 0:
                    self.extraction_results.append({
                        'file_id': None, # No hay archivo físico asociado
                        'filename': f"MySQL Table: {table_name}",
                        'df': df,
                        'rows': len(df)
                    })
                    logger.info(f"✓ MySQL: {len(df)} registros históricos recuperados para normalización")
                else:
                    logger.warning(f"Tabla MySQL {table_name} está vacía")
                
            except Exception as e:
                logger.error(f"Error leyendo datos de MySQL: {str(e)}", exc_info=True)
                return
            
        except Exception as e:
            logger.error(f"Error en _extract_from_mysql_db: {str(e)}", exc_info=True)

    def _insert_instituciones(self, df_clean: pd.DataFrame) -> int:
        """Inserta Dataframe limpio en tabla Institucion."""
        count = 0
        for _, row in df_clean.iterrows():
            try:
                # Convertir string JSON a dict para Django
                meta = json.loads(row['metadata']) if isinstance(row['metadata'], str) else {}
                
                # Usamos update_or_create por si corres el ETL varias veces
                Institucion.objects.update_or_create(
                    dane_ie_id=row['dane_ie_id'], # Llave única
                    defaults={
                        'id': row['id'], # Forzamos el UUID generado
                        'nombre': row['nombre'],
                        'direccion': row.get('direccion'),
                        'email': row.get('email'),
                        'estado': row.get('estado'),
                        'metadata': meta
                    }
                )
                count += 1
            except Exception as e:
                logger.warning(f"Error insertando IE {row.get('nombre')}: {e}")
        return count

    def _insert_sedes(self, df_clean: pd.DataFrame) -> int:
        """Inserta Dataframe limpio en tabla Sede."""
        count = 0
        for _, row in df_clean.iterrows():
            try:
                meta = json.loads(row['metadata']) if isinstance(row['metadata'], str) else {}
                
                Sede.objects.update_or_create(
                    dane_sede_id=row['dane_sede_id'],
                    defaults={
                        'id': row['id'],
                        'institucion_id': row['institucion_id'], # FK UUID
                        'nombre': row['nombre'],
                        'direccion': row.get('direccion'),
                        'lat': row.get('lat'),
                        'lon': row.get('lon'),
                        'estado': row.get('estado'),
                        'metadata': meta
                    }
                )
                count += 1
            except Exception as e:
                logger.warning(f"Error insertando Sede {row.get('dane_sede_id')}: {e}")
        return count

    def _insert_visitas(self, df_clean: pd.DataFrame) -> int:
        """Inserta Dataframe limpio en tabla Visita."""
        count = 0
        objs = []
        for _, row in df_clean.iterrows():
            try:
                if not row['sede_id']: continue # Saltar huérfanas
                
                meta = json.loads(row['metadata']) if isinstance(row['metadata'], str) else {}
                
                objs.append(Visita(
                    sede_id=row['sede_id'],
                    fecha=row['fecha'],
                    resultado=row['resultado'],
                    observaciones=row['observaciones'],
                    metadata=meta
                ))
            except Exception:
                continue
        
        # Bulk create es más rápido para visitas (son muchas)
        if objs:
            Visita.objects.bulk_create(objs, batch_size=500, ignore_conflicts=True)
            count = len(objs)
        return count
    
    def process_csv_data(self, df: pd.DataFrame, etl_file) -> tuple:
        """
        Procesa y carga datos CSV con validación de departamento.
        
        Returns:
            tuple: (procesados, removidos)
        """
        logger.info("=" * 60)
        logger.info("📋 PROCESANDO CSV")
        logger.info("=" * 60)
        
        try:
            # ⭐ PRIMERO: Normaliza nombres de columna
            logger.info("🧹 Normalizando nombres de columnas...")
            df.columns = [col.strip().upper() for col in df.columns]
            logger.debug(f"Columnas normalizadas: {df.columns.tolist()}")
            
            # ⭐ PASO 1: Validar departamento
            logger.info("🔍 Paso 1: Validando departamento...")
            
            # Detecta la columna de departamento (puede tener varios nombres)
            department_col = None
            for possible_name in ['DEPARTAMENTO', 'DEPT', 'DEPARTMENT', 'ID_DEPARTAMENTO']:
                if possible_name in df.columns:
                    department_col = possible_name
                    break
            
            if not department_col:
                logger.error("❌ No se encontró columna de departamento en CSV")
                raise ValueError("Columna DEPARTAMENTO no encontrada en CSV")
            
            initial_rows = len(df)
            df, removed, kept = DepartmentValidator.filter_dataframe(df, department_col)
            
            logger.info(f"✓ Departamento validado:")
            logger.info(f"  • Filas iniciales: {initial_rows}")
            logger.info(f"  • Filas del Valle del Cauca: {kept}")
            logger.info(f"  • Filas eliminadas: {removed}")
            
            if kept == 0:
                logger.warning("⚠️ ADVERTENCIA: No hay registros del Valle del Cauca en el archivo")
                return 0, initial_rows
            
            # ⭐ PASO 2: Normalizar y renombrar columnas
            logger.info("🔄 Paso 2: Normalizando columnas...")
            
            column_mapping = {
                'COD_DANE': 'codigo_dane_ie',
                'CODIGO_DANE_IE': 'codigo_dane_ie',
                'DANE_IE': 'codigo_dane_ie',
                'NOMBRE_INSTITUCION': 'nombre_institucion',
                'NOMBRE': 'nombre_institucion',
                'CORREO_INSTITUCIONAL': 'email',
                'CORREO': 'email',
                'EMAIL': 'email',
                'COD_SEDE_PRINCIPAL': 'codigo_dane_sede',
                'CODIGO_DANE_SEDE': 'codigo_dane_sede',
                'DANE_SEDE': 'codigo_dane_sede',
                'SEDE_PRINCIPAL': 'nombre_sede',
                'SEDE': 'nombre_sede',
                'DIRECCION': 'direccion',
                'DIR': 'direccion',
                'LATITUD': 'latitud',
                'LAT': 'latitud',
                'LONGITUD': 'longitud',
                'LON': 'longitud',
                'JORNADA': 'jornada',
                'ZONA': 'zona',
                'ESTADO': 'estado',
                'ID_MUNICIPIO': 'codigo_municipio',
                'CODIGO_MUNICIPIO': 'codigo_municipio',
                'MUNICIPIO': 'municipio',
                'TELEFONO': 'telefono',
                'TEL': 'telefono',
                department_col: 'nombre_departamento'
            }
            
            existing_mapping = {old: new for old, new in column_mapping.items() if old in df.columns}
            df = df.rename(columns=existing_mapping)
            logger.info(f"✓ {len(existing_mapping)} columnas normalizadas")
            logger.debug(f"Mapeo realizado: {existing_mapping}")
            logger.debug(f"Columnas finales: {df.columns.tolist()}")
            
            # ⭐ PASO 3: Cargar instituciones
            logger.info("📥 Paso 3: Cargando instituciones...")
            instituciones_cargadas = self._process_instituciones(df)
            
            # ⭐ PASO 4: Cargar sedes
            logger.info("📥 Paso 4: Cargando sedes...")
            sedes_cargadas = self._process_sedes(df)
            
            total_cargados = instituciones_cargadas + sedes_cargadas
            
            logger.info("=" * 60)
            logger.info(f"✅ CSV procesado correctamente")
            logger.info(f"  • Instituciones cargadas: {instituciones_cargadas}")
            logger.info(f"  • Sedes cargadas: {sedes_cargadas}")
            logger.info(f"  • Total: {total_cargados}")
            logger.info("=" * 60)
            
            return total_cargados, removed
        
        except Exception as e:
            logger.error(f"❌ Error procesando CSV: {str(e)}")
            raise
    
    def _process_instituciones(self, df: pd.DataFrame) -> int:
        """Procesa y carga instituciones (solo Valle del Cauca)."""
        logger.info("Procesando instituciones...")
        instituciones_cargadas = 0
        instituciones_fallidas = 0
        
        try:
            # Verificar que la columna existe
            if 'codigo_dane_ie' not in df.columns:
                logger.error(f"❌ Columna 'codigo_dane_ie' no encontrada. Disponibles: {df.columns.tolist()}")
                return 0
            
            # Deduplica por DANE
            unique_inst = df.drop_duplicates(subset=['codigo_dane_ie'])
            
            for _, row in unique_inst.iterrows():
                try:
                    # Validación 1: confirma que es Valle del Cauca
                    if not DepartmentValidator.is_valle_cauca(
                        row.get('nombre_departamento', ''),
                        row.get('codigo_departamento')
                    ):
                        logger.debug(f"  Institución descartada (no es Valle del Cauca): {row.get('nombre_institucion')}")
                        instituciones_fallidas += 1
                        continue
                    
                    # Validación 2: Verifica código de municipio (primeros 2 dígitos deben ser 76 para Valle del Cauca)
                    codigo_municipio = str(row.get('codigo_municipio', '')).strip()
                    if codigo_municipio and len(codigo_municipio) >= 2:
                        codigo_depto = codigo_municipio[:2]
                        if codigo_depto != '76':
                            logger.debug(f"  Institución descartada (municipio {codigo_municipio} no es del Valle del Cauca): {row.get('nombre_institucion')}")
                            instituciones_fallidas += 1
                            continue
                    
                    # Crea la institución
                    institucion_obj, created = Institucion.objects.update_or_create(
                        dane_ie_id=str(row.get('codigo_dane_ie', '')).strip(),
                        defaults={
                            'nombre': str(row.get('nombre_institucion', '')).strip(),
                            'codigo_municipio': codigo_municipio,
                            'direccion': str(row.get('direccion', '')).strip() if row.get('direccion') else None,
                            'telefono': str(row.get('telefono', '')).strip() if row.get('telefono') else None,
                            'email': str(row.get('email', '')).strip() if row.get('email') else None,
                            'estado': str(row.get('estado', 'A')).strip(),
                            'metadata': {
                                'origen': 'master_csv',
                                'departamento': str(row.get('nombre_departamento', '')).strip(),
                                'municipio': str(row.get('municipio', '')).strip() if row.get('municipio') else None
                            }
                        }
                    )
                    
                    instituciones_cargadas += 1
                    action = "creada" if created else "actualizada"
                    logger.debug(f"  ✓ Institución {action}: {row.get('nombre_institucion')}")
                
                except Exception as e:
                    logger.error(f"  ❌ Error cargando institución {row.get('codigo_dane_ie')}: {str(e)}")
                    instituciones_fallidas += 1
                    continue
            
            logger.info(f"✓ Instituciones: {instituciones_cargadas} cargadas, {instituciones_fallidas} errores")
            return instituciones_cargadas
        
        except Exception as e:
            logger.error(f"Error procesando instituciones: {str(e)}")
            return 0
    
    def _process_sedes(self, df: pd.DataFrame) -> int:
        """Procesa y carga sedes (solo del Valle del Cauca)."""
        logger.info("Procesando sedes...")
        sedes_cargadas = 0
        sedes_fallidas = 0
        
        try:
            # Obtén instituciones disponibles
            instituciones_dict = {ie.nombre.upper(): ie for ie in Institucion.objects.all()}
            
            if 'codigo_dane_sede' not in df.columns:
                logger.error(f"❌ Columna 'codigo_dane_sede' no encontrada. Disponibles: {df.columns.tolist()}")
                return 0
            
            # Deduplica por DANE sede
            unique_sedes = df.drop_duplicates(subset=['codigo_dane_sede'])
            
            for _, row in unique_sedes.iterrows():
                try:
                    # Validación 1: confirma que es Valle del Cauca
                    if not DepartmentValidator.is_valle_cauca(
                        row.get('nombre_departamento', ''),
                        row.get('codigo_departamento')
                    ):
                        logger.debug(f"  Sede descartada (no es Valle del Cauca): {row.get('nombre_sede')}")
                        sedes_fallidas += 1
                        continue
                    
                    # Validación 2: Verifica código de municipio
                    codigo_municipio = str(row.get('codigo_municipio', '')).strip()
                    if codigo_municipio and len(codigo_municipio) >= 2:
                        codigo_depto = codigo_municipio[:2]
                        if codigo_depto != '76':
                            logger.debug(f"  Sede descartada (municipio {codigo_municipio} no es del Valle del Cauca): {row.get('nombre_sede')}")
                            sedes_fallidas += 1
                            continue
                    
                    institucion_nombre = str(row.get('nombre_institucion', '')).strip().upper()
                    institucion = instituciones_dict.get(institucion_nombre)
                    
                    if not institucion:
                        logger.debug(f"  Sede descartada (institución no encontrada): {row.get('nombre_sede')}")
                        sedes_fallidas += 1
                        continue
                    
                    # Convierte coordenadas
                    try:
                        lat = float(str(row.get('latitud', '')).replace(',', '.')) if row.get('latitud') else None
                        lon = float(str(row.get('longitud', '')).replace(',', '.')) if row.get('longitud') else None
                    except:
                        lat, lon = None, None
                    
                    sede_obj, created = Sede.objects.update_or_create(
                        dane_sede_id=str(row.get('codigo_dane_sede', '')).strip(),
                        defaults={
                            'institucion_id': institucion.id,
                            'nombre': str(row.get('nombre_sede', '')).strip(),
                            'codigo_municipio': codigo_municipio,
                            'direccion': str(row.get('direccion', '')).strip() if row.get('direccion') else None,
                            'lat': lat,
                            'lon': lon,
                            'estado': str(row.get('estado', 'A')).strip(),
                            'metadata': {
                                'origen': 'master_csv',
                                'jornada': str(row.get('jornada', '')).strip() if row.get('jornada') else '',
                                'zona': str(row.get('zona', '')).strip() if row.get('zona') else '',
                                'departamento': str(row.get('nombre_departamento', '')).strip()
                            }
                        }
                    )
                    
                    sedes_cargadas += 1
                    action = "creada" if created else "actualizada"
                    logger.debug(f"  ✓ Sede {action}: {row.get('nombre_sede')}")
                
                except Exception as e:
                    logger.error(f"  ❌ Error cargando sede {row.get('codigo_dane_sede')}: {str(e)}")
                    sedes_fallidas += 1
                    continue
            
            logger.info(f"✓ Sedes: {sedes_cargadas} cargadas, {sedes_fallidas} errores")
            return sedes_cargadas
        
        except Exception as e:
            logger.error(f"Error procesando sedes: {str(e)}")
            raise


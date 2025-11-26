"""
Orchestrator: Coordina el flujo completo Extract-Transform-Load
================================================================

IMPLEMENTA INSTRUCTIVO DETALLADO: ETL CON SINCRONIZACIÓN MySQL + CSV

Arquitectura de datos:
- Fuente de verdad: MySQL (tiene identificacion = uesvalle_ie_id)
- Fuente complementaria: CSV del DANE (tiene COD_DANE)

Orden de procesamiento (CRÍTICO - no cambiar):
  1️⃣ CARGAR MUNICIPIOS
  2️⃣ CARGAR INSTITUCIONES (MySQL + CSV merge)
  3️⃣ CARGAR SEDES (CSV vinculadas a instituciones)  
  4️⃣ CARGAR VISITAS (MySQL vinculadas a instituciones/sedes)

Responsabilidades:
- Orquestar fases E-T-L en secuencia
- Actualizar estado de ETLRun
- Registrar errores y métricas
- Coordinar sincronización MySQL + CSV
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
from .sync_processor import MySQLCSVSyncProcessor, ETLMetrics

logger = logging.getLogger('etl.orchestrator')


class ETLOrchestrator:
    """
    Coordina el pipeline ETL completo con sincronización MySQL + CSV.
    
    Flujo según instructivo:
      1. Extract: Obtener datos de MySQL y CSV
      2. Transform: Validar y normalizar (merge MySQL + CSV)
      3. Load: Persistir en orden: Instituciones → Sedes → Visitas
    
    Uso:
        orchestrator = ETLOrchestrator(etl_run_id=1)
        success = orchestrator.execute()
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
        self.dict_instituciones_by_uesvalle = {}  # Nuevo: mapeo uesvalle_ie_id → UUID
        
        # Sincronizador MySQL + CSV
        self.sync_processor: Optional[MySQLCSVSyncProcessor] = None
        self.etl_metrics: Optional[ETLMetrics] = None
    
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
                            # No pasar encoding fijo para permitir fallback automático
                            df = RobustCSVParser.parse_csv(etl_file.file_path, delimiter=';')
                            
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
                    
                    # Limpiar espacios en blanco en columnas de texto (con manejo seguro)
                    for col in df_valid.select_dtypes(include=['object']).columns:
                        try:
                            # Solo aplicar .str si realmente son strings
                            if df_valid[col].dtype == 'object':
                                df_valid[col] = df_valid[col].astype(str).str.strip()
                                # Restaurar NaN donde había valores vacíos
                                df_valid[col] = df_valid[col].replace(['nan', 'None', ''], pd.NA)
                        except Exception:
                            pass  # Ignorar columnas problemáticas
                            
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
        """
        Carga datos usando BULK OPERATIONS (optimizado para alto volumen).
        
        FLUJO SIMPLIFICADO:
          1️⃣ Indexar CSV por CODIGODANE (para enriquecer con coordenadas)
          2️⃣ Extraer TODA la data de MySQL en memoria
          3️⃣ BULK crear/actualizar INSTITUCIONES (sin sedes)
          4️⃣ BULK crear VISITAS
          
        NO SE USAN SEDES - cada fila MySQL = 1 institución + 1 visita
        Coordenadas van directamente en la tabla institucion
        """
        try:
            logger.info(f"Cargando datos a BD ({'DRY RUN' if dry_run else 'LIVE'})...")
            logger.info("🚀 Usando BULK OPERATIONS para alto rendimiento")
            
            # Separar archivos por tipo
            csv_files = []
            mysql_files = []
            
            for transformation in self.transformation_results:
                df = transformation['df_transformed']
                filename = transformation['filename']
                
                if self._is_mysql_data(df) or 'MySQL' in filename:
                    mysql_files.append(transformation)
                    logger.info(f"  📊 MySQL data: {filename} ({len(df)} registros)")
                else:
                    csv_files.append(transformation)
                    logger.info(f"  📄 CSV data: {filename} ({len(df)} registros)")
            
            # =========================================================
            # PASO 1: Indexar CSV por CODIGODANE (para coordenadas)
            # =========================================================
            logger.info("\n" + "=" * 60)
            logger.info("📋 PASO 1: Indexando CSV por CODIGODANE...")
            logger.info("=" * 60)
            
            csv_by_dane = {}
            for csv_data in csv_files:
                df = csv_data['df_transformed'].copy()
                # Normalizar nombres de columnas a mayúsculas
                df.columns = [str(c).upper().strip() for c in df.columns]
                
                logger.debug(f"   Columnas CSV disponibles: {list(df.columns)[:10]}...")
                
                # Buscar columna de DANE (más flexible)
                dane_col = None
                for col in df.columns:
                    col_upper = col.upper()
                    if 'COD_DANE' in col_upper or col_upper == 'CODIGODANE' or col_upper == 'DANE' or 'CODIGO_DANE' in col_upper:
                        dane_col = col
                        logger.debug(f"   Columna DANE encontrada: {col}")
                        break
                
                if dane_col:
                    for _, row in df.iterrows():
                        dane = str(row.get(dane_col, '')).strip()
                        # Limpiar formato .0 de números convertidos a string
                        if dane.endswith('.0'):
                            dane = dane[:-2]
                        if dane and dane.lower() not in ['nan', 'none', '', 'na']:
                            csv_by_dane[dane] = row
                else:
                    logger.warning(f"   ⚠️ No se encontró columna DANE en CSV. Columnas: {list(df.columns)}")
            
            logger.info(f"✓ CSV indexado: {len(csv_by_dane)} registros por DANE")
            
            # =========================================================
            # PASO 2: Extraer TODA la data de MySQL
            # =========================================================
            logger.info("\n" + "=" * 60)
            logger.info("📊 PASO 2: Extrayendo datos de MySQL...")
            logger.info("=" * 60)
            
            df_mysql = None
            for mysql_data in mysql_files:
                df_temp = mysql_data['df_transformed'].copy()
                df_temp.columns = [str(c).lower().strip() for c in df_temp.columns]
                if df_mysql is None:
                    df_mysql = df_temp
                else:
                    df_mysql = pd.concat([df_mysql, df_temp], ignore_index=True)
            
            # Si no hay datos de MySQL en transformation_results, intentar extraer directamente
            if (df_mysql is None or df_mysql.empty) and 'source_mysql' in settings.DATABASES:
                logger.info("   Intentando extracción directa de MySQL...")
                try:
                    conn = connections['source_mysql']
                    if conn.connection is None:
                        conn.connect()
                    df_mysql = pd.read_sql("SELECT * FROM visitas_instituciones_educativos", conn.connection)
                    df_mysql.columns = [str(c).lower().strip() for c in df_mysql.columns]
                    logger.info(f"   ✓ MySQL directo: {len(df_mysql)} registros")
                except Exception as e:
                    logger.error(f"   ❌ Error extracción directa MySQL: {e}")
            
            if df_mysql is None or df_mysql.empty:
                logger.warning("⚠️ No hay datos de MySQL para procesar")
                return True
            
            logger.info(f"✓ MySQL: {len(df_mysql)} registros totales")
            
            # =========================================================
            # PASO 3: BULK crear/actualizar INSTITUCIONES
            # =========================================================
            logger.info("\n" + "=" * 60)
            logger.info("🏫 PASO 3: BULK creando instituciones...")
            logger.info("=" * 60)
            
            inst_created, inst_updated = self._bulk_create_instituciones(df_mysql, csv_by_dane)
            
            logger.info(f"✓ Instituciones: {inst_created} creadas, {inst_updated} actualizadas")
            
            # =========================================================
            # PASO 4: BULK crear VISITAS
            # =========================================================
            logger.info("\n" + "=" * 60)
            logger.info("📝 PASO 4: BULK creando visitas...")
            logger.info("=" * 60)
            
            visitas_created, visitas_updated = self._bulk_create_visitas(df_mysql)
            
            logger.info(f"✓ Visitas: {visitas_created} creadas, {visitas_updated} actualizadas")
            
            # =========================================================
            # RESUMEN FINAL
            # =========================================================
            logger.info("\n" + "=" * 60)
            logger.info("📊 RESUMEN ETL COMPLETADO (BULK)")
            logger.info("=" * 60)
            logger.info(f"   Instituciones creadas: {inst_created}")
            logger.info(f"   Instituciones actualizadas: {inst_updated}")
            logger.info(f"   Visitas creadas: {visitas_created}")
            logger.info(f"   Visitas actualizadas: {visitas_updated}")
            logger.info("=" * 60)
            
            # Actualizar archivos ETL
            for transformation in self.transformation_results:
                file_id = transformation.get('file_id')
                if file_id:
                    ETLFile.objects.filter(id=file_id).update(
                        status='completed',
                        processed_at=timezone.now()
                    )
            
            return True
        
        except Exception as e:
            logger.error(f"Error en carga BULK: {str(e)}", exc_info=True)
            return False
    
    def _bulk_create_instituciones(self, df_mysql: pd.DataFrame, csv_by_dane: dict) -> tuple:
        """
        BULK crear/actualizar instituciones desde MySQL + enriquecer con CSV.
        
        Returns:
            (created_count, updated_count)
        """
        BATCH_SIZE = 500
        
        # 1. Obtener instituciones únicas de MySQL
        if 'identificacion' not in df_mysql.columns:
            logger.warning("No hay columna 'identificacion' en MySQL")
            return (0, 0)
        
        df_unique = df_mysql.drop_duplicates(subset=['identificacion'])
        logger.info(f"   Instituciones únicas a procesar: {len(df_unique)}")
        
        # 2. Cargar instituciones existentes en memoria (por uesvalle_ie_id y dane_ie_id)
        existing_by_uesvalle = {
            inst.uesvalle_ie_id: inst 
            for inst in Institucion.objects.filter(uesvalle_ie_id__isnull=False)
        }
        existing_by_dane = {
            inst.dane_ie_id: inst 
            for inst in Institucion.objects.filter(dane_ie_id__isnull=False)
        }
        
        logger.info(f"   Existentes: {len(existing_by_uesvalle)} por UESValle, {len(existing_by_dane)} por DANE")
        
        # Log columns for debugging
        logger.info(f"   Columnas disponibles en MySQL: {list(df_mysql.columns)}")

        to_create = []
        to_update = []
        
        for _, row in df_unique.iterrows():
            uesvalle_id = str(row.get('identificacion', '')).strip()
            if not uesvalle_id or uesvalle_id.lower() in ['nan', 'none', '']:
                continue
            
            # Obtener codigodane
            codigodane = None
            if 'codigodane' in row.index and pd.notna(row.get('codigodane')):
                codigodane = str(row['codigodane']).strip()
                if codigodane.lower() in ['nan', 'none', '']:
                    codigodane = None
            
            # Buscar nombre
            nombre = None
            # Prioridad según esquema MySQL: nombreestablecimiento
            for col in ['nombreestablecimiento', 'nombreinstitucion', 'nombre_institucion', 'nombre', 'razonsocial', 'establecimiento', 'institucion']:
                if col in row.index and pd.notna(row.get(col)):
                    nombre = str(row[col]).strip()
                    break
            if not nombre:
                nombre = f"Institución {uesvalle_id}"
            
            # Buscar coordenadas en CSV (por DANE)
            lat, lon = None, None
            if codigodane and codigodane in csv_by_dane:
                csv_row = csv_by_dane[codigodane]
                # Buscar columnas de coordenadas
                for lat_col in ['LATITUD', 'LAT', 'LATITUDE']:
                    if lat_col in csv_row.index:
                        lat = self._parse_coordinate(csv_row.get(lat_col))
                        break
                for lon_col in ['LONGITUD', 'LON', 'LONGITUDE', 'LNG']:
                    if lon_col in csv_row.index:
                        lon = self._parse_coordinate(csv_row.get(lon_col))
                        break
            
            # Verificar si existe
            existing = existing_by_uesvalle.get(uesvalle_id)
            if not existing and codigodane:
                existing = existing_by_dane.get(codigodane)
            
            if existing:
                # Actualizar
                existing.nombre = nombre
                existing.uesvalle_ie_id = uesvalle_id
                if codigodane:
                    existing.dane_ie_id = codigodane
                if lat is not None:
                    existing.lat = lat
                if lon is not None:
                    existing.lon = lon
                existing.estado = 'ACTIVA'
                existing.metadata = {'origen': 'mysql+csv', 'fecha_sync': timezone.now().isoformat()}
                to_update.append(existing)
            else:
                # Crear nueva
                to_create.append(Institucion(
                    id=uuid.uuid4(),
                    nombre=nombre,
                    uesvalle_ie_id=uesvalle_id,
                    dane_ie_id=codigodane,
                    lat=lat,
                    lon=lon,
                    estado='ACTIVA',
                    metadata={'origen': 'mysql+csv', 'fecha_sync': timezone.now().isoformat()}
                ))
        
        # 3. Ejecutar BULK operations
        created_count = 0
        updated_count = 0
        
        # BULK CREATE
        if to_create:
            for i in range(0, len(to_create), BATCH_SIZE):
                batch = to_create[i:i+BATCH_SIZE]
                Institucion.objects.bulk_create(batch, ignore_conflicts=True)
                created_count += len(batch)
                logger.info(f"   Batch {i//BATCH_SIZE + 1}: {len(batch)} instituciones creadas")
        
        # BULK UPDATE
        if to_update:
            for i in range(0, len(to_update), BATCH_SIZE):
                batch = to_update[i:i+BATCH_SIZE]
                Institucion.objects.bulk_update(
                    batch, 
                    ['nombre', 'uesvalle_ie_id', 'dane_ie_id', 'lat', 'lon', 'estado', 'metadata'],
                    batch_size=BATCH_SIZE
                )
                updated_count += len(batch)
                logger.info(f"   Batch {i//BATCH_SIZE + 1}: {len(batch)} instituciones actualizadas")
        
        return (created_count, updated_count)
    
    def _bulk_create_visitas(self, df_mysql: pd.DataFrame) -> tuple:
        """
        BULK crear/actualizar visitas desde MySQL.
        
        Returns:
            (created_count, updated_count)
        """
        BATCH_SIZE = 500
        
        # 1. Recargar diccionario de instituciones
        inst_by_uesvalle = {
            inst.uesvalle_ie_id: inst.id 
            for inst in Institucion.objects.filter(uesvalle_ie_id__isnull=False)
        }
        
        logger.info(f"   Instituciones disponibles: {len(inst_by_uesvalle)}")
        
        # 2. Cargar visitas existentes (por clave única: institucion + fecha + programa)
        existing_visitas = {}
        for v in Visita.objects.all().values('id', 'institucion_id', 'fechavisita', 'programa'):
            key = (str(v['institucion_id']), str(v['fechavisita']), v['programa'] or '')
            existing_visitas[key] = v['id']
        
        logger.info(f"   Visitas existentes: {len(existing_visitas)}")
        
        to_create = []
        to_update = []
        skipped = 0
        
        for _, row in df_mysql.iterrows():
            # Obtener institucion_id
            uesvalle_id = str(row.get('identificacion', '')).strip()
            if not uesvalle_id or uesvalle_id.lower() in ['nan', 'none', '']:
                skipped += 1
                continue
            
            institucion_id = inst_by_uesvalle.get(uesvalle_id)
            if not institucion_id:
                skipped += 1
                continue
            
            # Obtener fecha
            fechavisita = row.get('fechavisita')
            if pd.isna(fechavisita) or not fechavisita:
                skipped += 1
                continue
            
            # Programa
            programa = str(row.get('programa', '')).strip() if pd.notna(row.get('programa')) else ''
            
            # Clave única
            key = (str(institucion_id), str(fechavisita), programa)
            
            # Metadata
            meta = {}
            # Campos adicionales del esquema MySQL
            meta_cols = [
                'codigodane', 'codigodanesede', 'nombrefuncionario', 'apellidofuncionario',
                'direccionestablecimiento', 'telefonoestablecimiento', 'celular',
                'codigoactividad', 'idactividad', 'codigocomuna', 'nombrecomuna', 'codigomunicipio', 'nombremunicipio',
                'nombrecorregimiento', 'codigocorregimiento', 'nombrerepresentante', 'apellidorepresentante',
                'codigoaro', 'nombrearo', 'numeropiscinas', 'nombrebarrio', 'ideisobjetosprogramatico',
                'numeromanualacta', 'plazo', 'cumplimiento', 'tienepae', 'estudianteshombre', 'estudiantesmujer',
                'numerosdocente', 'totaltrabajador', 'fecha_cargue', 'tipocontrato', 'nombreusuario'
            ]
            for col in meta_cols:
                if col in row.index and pd.notna(row.get(col)):
                    meta[col] = str(row[col])
            
            # Convertir campos de tipo INT de forma segura
            codigofuncionario = None
            codigotipoobjeto = None
            
            # Concepto visita (Sanitizar para cumplir CHECK constraint)
            conceptovisita = row.get('conceptovisita')
            if pd.notna(conceptovisita):
                conceptovisita = str(conceptovisita).strip().upper()
                if conceptovisita not in ['F', 'D', 'FCR']:
                    # Si no es válido, intentar mapear o dejar en None
                    # 'SC' -> Sin Concepto -> None
                    conceptovisita = None
            else:
                conceptovisita = None
            
            # Parsear codigofuncionario
            if pd.notna(row.get('codigofuncionario')):
                try:
                    val = row.get('codigofuncionario')
                    # Si es float, convertir a int
                    if isinstance(val, float):
                        val = int(val)
                    elif isinstance(val, str):
                        val = int(float(val))  # Manejar "123.0"
                    # Validar que esté dentro del rango de INT
                    if -2147483648 <= val <= 2147483647:
                        codigofuncionario = val
                except (ValueError, TypeError, OverflowError):
                    codigofuncionario = None
            
            # Parsear codigotipoobjeto
            if pd.notna(row.get('codigotipoobjeto')):
                try:
                    val = row.get('codigotipoobjeto')
                    if isinstance(val, float):
                        val = int(val)
                    elif isinstance(val, str):
                        val = int(float(val))
                    if -2147483648 <= val <= 2147483647:
                        codigotipoobjeto = val
                except (ValueError, TypeError, OverflowError):
                    codigotipoobjeto = None
            
            if key in existing_visitas:
                # Si el ID es None, significa que se agregó a to_create en este mismo loop
                if existing_visitas[key] is None:
                    continue

                # Actualizar existente
                visita = Visita(
                    id=existing_visitas[key],
                    institucion_id=institucion_id,
                    fechavisita=fechavisita,
                    programa=programa,
                    nombreactividad=row.get('nombreactividad') if pd.notna(row.get('nombreactividad')) else None,
                    codigotipoobjeto=codigotipoobjeto,
                    nombretipoobjeto=row.get('nombretipoobjeto') if pd.notna(row.get('nombretipoobjeto')) else None,
                    conceptovisita=conceptovisita,
                    requerimientos=row.get('requerimientos') if pd.notna(row.get('requerimientos')) else None,
                    motivovisita=row.get('motivovisita') if pd.notna(row.get('motivovisita')) else None,
                    nombrefuncionario=row.get('nombrefuncionario') if pd.notna(row.get('nombrefuncionario')) else None,
                    apellidofuncionario=row.get('apellidofuncionario') if pd.notna(row.get('apellidofuncionario')) else None,
                    codigofuncionario=codigofuncionario,
                    resultado=row.get('resultado') if pd.notna(row.get('resultado')) else (str(row.get('cumplimiento')) if pd.notna(row.get('cumplimiento')) else None),
                    observacion=row.get('observacion') if pd.notna(row.get('observacion')) else None,
                    metadata=meta
                )
                to_update.append(visita)
            else:
                # Crear nueva
                to_create.append(Visita(
                    # id=uuid.uuid4(),  # REMOVED: Let DB handle BigAutoField
                    institucion_id=institucion_id,
                    fechavisita=fechavisita,
                    programa=programa,
                    nombreactividad=row.get('nombreactividad') if pd.notna(row.get('nombreactividad')) else None,
                    codigotipoobjeto=codigotipoobjeto,
                    nombretipoobjeto=row.get('nombretipoobjeto') if pd.notna(row.get('nombretipoobjeto')) else None,
                    conceptovisita=conceptovisita,
                    requerimientos=row.get('requerimientos') if pd.notna(row.get('requerimientos')) else None,
                    motivovisita=row.get('motivovisita') if pd.notna(row.get('motivovisita')) else None,
                    nombrefuncionario=row.get('nombrefuncionario') if pd.notna(row.get('nombrefuncionario')) else None,
                    apellidofuncionario=row.get('apellidofuncionario') if pd.notna(row.get('apellidofuncionario')) else None,
                    codigofuncionario=codigofuncionario,
                    resultado=row.get('resultado') if pd.notna(row.get('resultado')) else (str(row.get('cumplimiento')) if pd.notna(row.get('cumplimiento')) else None),
                    observacion=row.get('observacion') if pd.notna(row.get('observacion')) else None,
                    metadata=meta
                ))
                # Agregar al índice para evitar duplicados en el mismo batch
                existing_visitas[key] = None
        
        logger.info(f"   Saltadas (sin institución o fecha): {skipped}")
        
        # 3. Ejecutar BULK operations
        created_count = 0
        updated_count = 0
        
        # BULK CREATE
        if to_create:
            for i in range(0, len(to_create), BATCH_SIZE):
                batch = to_create[i:i+BATCH_SIZE]
                Visita.objects.bulk_create(batch, ignore_conflicts=True)
                created_count += len(batch)
                logger.info(f"   Batch {i//BATCH_SIZE + 1}: {len(batch)} visitas creadas")
        
        # BULK UPDATE
        if to_update:
            for i in range(0, len(to_update), BATCH_SIZE):
                batch = to_update[i:i+BATCH_SIZE]
                Visita.objects.bulk_update(
                    batch,
                    ['nombreactividad', 'codigotipoobjeto', 'nombretipoobjeto', 'conceptovisita', 
                     'requerimientos', 'motivovisita', 'nombrefuncionario', 'apellidofuncionario', 
                     'codigofuncionario', 'resultado', 'observacion', 'metadata'],
                    batch_size=BATCH_SIZE
                )
                updated_count += len(batch)
                logger.info(f"   Batch {i//BATCH_SIZE + 1}: {len(batch)} visitas actualizadas")
        
        return (created_count, updated_count)
    
    def _parse_coordinate(self, val) -> float:
        """Parsea un valor de coordenada a float."""
        if val is None or pd.isna(val):
            return None
        try:
            # Manejar formato con coma decimal
            if isinstance(val, str):
                val = val.replace(',', '.').strip()
            return float(val)
        except (ValueError, TypeError):
            return None
    
    def _is_mysql_data(self, df: pd.DataFrame) -> bool:
        """Detecta si el DataFrame viene de MySQL (tiene columnas características de visitas)."""
        cols_lower = [c.lower() for c in df.columns]
        mysql_indicators = ['identificacion', 'fechavisita', 'conceptovisita', 'codigofuncionario']
        return any(ind in cols_lower for ind in mysql_indicators)


    def _load_dictionaries(self):
        """
        Carga diccionarios de mapeo para sincronización MySQL + CSV.
        
        Diccionarios cargados:
          - dict_instituciones: dane_ie_id → UUID
          - dict_instituciones_by_uesvalle: uesvalle_ie_id → UUID
          - dict_sedes: dane_sede_id → UUID
          - dict_instituciones_by_name: nombre → UUID
        """
        # Por DANE (fuente CSV)
        self.dict_instituciones = {
            inst.dane_ie_id: str(inst.id) 
            for inst in Institucion.objects.filter(dane_ie_id__isnull=False)
        }
        
        # Por uesvalle_ie_id (fuente MySQL - identificacion)
        self.dict_instituciones_by_uesvalle = {
            inst.uesvalle_ie_id: str(inst.id) 
            for inst in Institucion.objects.filter(uesvalle_ie_id__isnull=False)
        }
        
        # Sedes por DANE
        self.dict_sedes = {
            sede.dane_sede_id: str(sede.id) 
            for sede in Sede.objects.filter(dane_sede_id__isnull=False)
        }
        
        # Instituciones por nombre (fallback)
        self.dict_instituciones_by_name = {
            inst.nombre: str(inst.id) 
            for inst in Institucion.objects.all()
        }
        
        logger.info(f"📚 Diccionarios cargados: {len(self.dict_instituciones)} IEs (DANE), "
                   f"{len(self.dict_instituciones_by_uesvalle)} IEs (UESValle), "
                   f"{len(self.dict_sedes)} Sedes")

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
        """
        Procesa Visitas desde MySQL con nueva lógica de sincronización.
        
        Implementa FASE 4 del instructivo:
        - institucion_id OBLIGATORIO
        - sede_id OPCIONAL (puede ser NULL)
        - Búsqueda por: 1) codigodane, 2) identificacion (uesvalle_ie_id)
        """
        logger.info(f"📋 Procesando Visitas (Normalizando {len(df)} registros)...")
        logger.info(f"   Instituciones disponibles: {len(self.dict_instituciones)} (DANE), "
                   f"{len(self.dict_instituciones_by_uesvalle)} (UESValle)")
        logger.info(f"   Sedes disponibles: {len(self.dict_sedes)}")
        
        if len(df) == 0:
            logger.warning("⚠️ No hay registros de visitas para procesar")
            return 0
        
        # Usar transformar_visitas_mysql con diccionarios de instituciones
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df_visitas = transformar_visitas_mysql(
            df,
            self.dict_sedes,
            dict_instituciones_by_dane=self.dict_instituciones,
            dict_instituciones_by_uesvalle=self.dict_instituciones_by_uesvalle
        )
        
        if df_visitas.empty:
            logger.warning("⚠️ No se pudieron procesar visitas (DataFrame vacío)")
            return 0
        
        # Insertar visitas procesadas
        return self._insert_visitas(df_visitas)
    
    def _process_visitas_legacy(self, df: pd.DataFrame) -> int:
        """
        DEPRECATED: Método legacy para procesar visitas.
        Usar _process_visitas() con la nueva lógica.
        """
        logger.warning("⚠️ Usando método legacy _process_visitas_legacy - considerar migrar a _process_visitas")
        
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
            logger.info("=" * 60)
            logger.info("🔌 Intentando extraer datos directamente de MySQL...")
            logger.info("=" * 60)
            
            # Verificar configuración
            logger.info(f"   Databases configuradas: {list(settings.DATABASES.keys())}")
            
            if 'source_mysql' not in settings.DATABASES:
                logger.warning("❌ 'source_mysql' no está en settings.DATABASES")
                return
            
            logger.info("   ✓ source_mysql está configurado en settings")
            
            # Obtener conexión
            conn = connections['source_mysql']
            logger.info(f"   Conexión obtenida: {conn}")
            
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
        """
        Inserta Dataframe limpio en tabla Visita.
        
        Campos del modelo actualizado:
          - institucion_id (OBLIGATORIO)
          - sede_id (OPCIONAL)
          - fechavisita (OBLIGATORIO)
          - nombreactividad, codigotipoobjeto, nombretipoobjeto
          - conceptovisita (F/D/FCR)
          - requerimientos, motivovisita
          - nombrefuncionario, apellidofuncionario, codigofuncionario
          - programa, resultado, observacion
          - metadata
        """
        if df_clean.empty:
            logger.warning("DataFrame de visitas vacío")
            return 0
        
        count = 0
        count_creadas = 0
        count_actualizadas = 0
        count_fallidas = 0
        
        for _, row in df_clean.iterrows():
            try:
                # institucion_id es OBLIGATORIO
                institucion_id = row.get('institucion_id')
                if not institucion_id:
                    logger.debug(f"Visita sin institucion_id, saltando")
                    count_fallidas += 1
                    continue
                
                # fechavisita es OBLIGATORIO
                fechavisita = row.get('fechavisita')
                if not fechavisita:
                    logger.debug(f"Visita sin fechavisita, saltando")
                    count_fallidas += 1
                    continue
                
                # sede_id es OPCIONAL
                sede_id = row.get('sede_id') or None
                
                # Programa para índice único
                programa = row.get('programa') or ''
                
                # Metadata
                meta = row.get('metadata', {})
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except:
                        meta = {}
                
                # Usar update_or_create para manejar duplicados según índice único
                # (sede_id, fechavisita, programa)
                obj, created = Visita.objects.update_or_create(
                    sede_id=sede_id,
                    fechavisita=fechavisita,
                    programa=programa,
                    defaults={
                        'institucion_id': institucion_id,
                        'nombreactividad': row.get('nombreactividad'),
                        'codigotipoobjeto': row.get('codigotipoobjeto'),
                        'nombretipoobjeto': row.get('nombretipoobjeto'),
                        'conceptovisita': row.get('conceptovisita'),
                        'requerimientos': row.get('requerimientos'),
                        'motivovisita': row.get('motivovisita'),
                        'nombrefuncionario': row.get('nombrefuncionario'),
                        'apellidofuncionario': row.get('apellidofuncionario'),
                        'codigofuncionario': row.get('codigofuncionario'),
                        'resultado': row.get('resultado'),
                        'observacion': row.get('observacion'),
                        'metadata': meta
                    }
                )
                
                if created:
                    count_creadas += 1
                else:
                    count_actualizadas += 1
                count += 1
                
            except Exception as e:
                logger.warning(f"Error insertando visita: {e}")
                count_fallidas += 1
                continue
        
        logger.info(f"✓ Visitas: {count_creadas} creadas, {count_actualizadas} actualizadas, {count_fallidas} fallidas")
        return count

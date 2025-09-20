"""
Servicios ETL para extracción, transformación y carga de datos.
Implementa el pipeline: MySQL + Excel → normaliza → carga en Supabase (Postgres).
"""
import os
import pandas as pd
from hashlib import sha256
from typing import Dict, List, Optional, Any
from django.db import connections, transaction
from django.conf import settings
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
import logging

from .models import (
    ETLRun, DimMunicipio, DimSede, FactInstitucion, 
    ChangeLog, StgInstitucionMySQL
)

logger = logging.getLogger(__name__)


class MySQLExtractor:
    """Extractor de datos desde MySQL."""
    
    @staticmethod
    def extract_instituciones() -> List[Dict[str, Any]]:
        """
        Extrae instituciones educativas desde MySQL.
        Retorna lista de diccionarios con los datos.
        """
        sql = """
        SELECT 
            codigo_dane,
            nombre,
            municipio_codigo,
            estado,
            sector,
            zona,
            direccion,
            telefono,
            email,
            latitud,
            longitud,
            created_at,
            updated_at
        FROM instituciones_educativas
        WHERE estado IS NOT NULL
        """
        
        try:
            with connections["source_mysql"].cursor() as cursor:
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
            # Convertir a lista de diccionarios
            data = [dict(zip(columns, row)) for row in rows]
            
            logger.info(f"Extraídos {len(data)} registros desde MySQL")
            return data
            
        except Exception as e:
            logger.error(f"Error extrayendo datos de MySQL: {e}")
            raise
    
    @staticmethod
    def extract_municipios() -> List[Dict[str, Any]]:
        """Extrae catálogo de municipios desde MySQL."""
        sql = """
        SELECT 
            codigo_dane as codigo,
            nombre,
            departamento_codigo,
            departamento_nombre
        FROM municipios
        ORDER BY departamento_nombre, nombre
        """
        
        try:
            with connections["source_mysql"].cursor() as cursor:
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
            data = [dict(zip(columns, row)) for row in rows]
            logger.info(f"Extraídos {len(data)} municipios desde MySQL")
            return data
            
        except Exception as e:
            logger.error(f"Error extrayendo municipios de MySQL: {e}")
            raise


class ExcelExtractor:
    """Extractor de datos desde archivos Excel."""
    
    @staticmethod
    def read_excel_file(file_path: str, sheet_name: str = 0) -> pd.DataFrame:
        """
        Lee archivo Excel y retorna DataFrame.
        
        Args:
            file_path: Ruta al archivo Excel
            sheet_name: Nombre o índice de la hoja
            
        Returns:
            DataFrame con los datos del Excel
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
            
            # Configuración específica para leer Excel
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                dtype={
                    "codigo_dane": "string",
                    "municipio_codigo": "string",
                    "telefono": "string"
                },
                engine="openpyxl"  # Para archivos .xlsx
            )
            
            logger.info(f"Leído archivo Excel {file_path}: {len(df)} filas")
            return df
            
        except Exception as e:
            logger.error(f"Error leyendo Excel {file_path}: {e}")
            raise
    
    @staticmethod
    def extract_excel_a(file_path: str) -> pd.DataFrame:
        """Extrae datos del Excel A con normalización específica."""
        df = ExcelExtractor.read_excel_file(file_path)
        
        # Normalizar nombres de columnas para Excel A
        column_mapping = {
            "CODIGO_DANE": "codigo_dane",
            "NOMBRE_IE": "nombre",
            "MUNICIPIO_COD": "municipio_codigo",
            "ESTADO_IE": "estado",
            # Agregar más mapeos según estructura real
        }
        
        df = df.rename(columns=column_mapping)
        return df
    
    @staticmethod
    def extract_excel_b(file_path: str) -> pd.DataFrame:
        """Extrae datos del Excel B con normalización específica."""
        df = ExcelExtractor.read_excel_file(file_path)
        
        # Normalizar nombres de columnas para Excel B
        column_mapping = {
            "CodDANE": "codigo_dane",
            "NombreInstitucion": "nombre",
            "CodMunicipio": "municipio_codigo",
            "EstadoIE": "estado",
            # Agregar más mapeos según estructura real
        }
        
        df = df.rename(columns=column_mapping)
        return df


class DataTransformer:
    """Transformador de datos - normalización y limpieza."""
    
    @staticmethod
    def transform_instituciones(mysql_data: List[Dict], 
                               excel_a: pd.DataFrame, 
                               excel_b: pd.DataFrame) -> pd.DataFrame:
        """
        Transforma y unifica datos de las tres fuentes.
        
        Args:
            mysql_data: Datos desde MySQL
            excel_a: DataFrame de Excel A
            excel_b: DataFrame de Excel B
            
        Returns:
            DataFrame normalizado y listo para carga
        """
        try:
            # Convertir MySQL data a DataFrame
            df_mysql = pd.DataFrame(mysql_data)
            if not df_mysql.empty:
                df_mysql['source_system'] = 'mysql'
            
            # Preparar DataFrames de Excel
            excel_a = excel_a.copy()
            excel_b = excel_b.copy()
            
            if not excel_a.empty:
                excel_a['source_system'] = 'excel_a'
            if not excel_b.empty:
                excel_b['source_system'] = 'excel_b'
            
            # Definir columnas comunes requeridas
            required_columns = [
                "codigo_dane", "nombre", "municipio_codigo", "estado", 
                "source_system"
            ]
            
            # Asegurar que todas las fuentes tienen las columnas requeridas
            for df in [df_mysql, excel_a, excel_b]:
                for col in required_columns:
                    if col not in df.columns:
                        df[col] = None
            
            # Unificar DataFrames
            dfs_to_concat = []
            if not df_mysql.empty:
                dfs_to_concat.append(df_mysql[required_columns + 
                    [col for col in df_mysql.columns if col not in required_columns]])
            if not excel_a.empty:
                dfs_to_concat.append(excel_a[required_columns + 
                    [col for col in excel_a.columns if col not in required_columns]])
            if not excel_b.empty:
                dfs_to_concat.append(excel_b[required_columns + 
                    [col for col in excel_b.columns if col not in required_columns]])
            
            if not dfs_to_concat:
                return pd.DataFrame()
            
            df_unified = pd.concat(dfs_to_concat, ignore_index=True)
            
            # Aplicar transformaciones y limpieza
            df_clean = DataTransformer._clean_data(df_unified)
            
            # Generar hash para detección de cambios
            df_clean = DataTransformer._generate_hash(df_clean)
            
            logger.info(f"Transformación completada: {len(df_clean)} registros")
            return df_clean
            
        except Exception as e:
            logger.error(f"Error en transformación de datos: {e}")
            raise
    
    @staticmethod
    def _clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """Aplica limpieza y normalización a los datos."""
        df = df.copy()
        
        # Limpiar código DANE
        if 'codigo_dane' in df.columns:
            df['codigo_dane'] = df['codigo_dane'].astype(str).str.strip()
            df['codigo_dane'] = df['codigo_dane'].replace('nan', None)
        
        # Limpiar nombres
        if 'nombre' in df.columns:
            df['nombre'] = df['nombre'].astype(str).str.strip()
            df['nombre'] = df['nombre'].str.title()
            df['nombre'] = df['nombre'].replace('nan', None)
        
        # Normalizar estados
        if 'estado' in df.columns:
            df['estado'] = df['estado'].astype(str).str.strip().str.title()
            # Mapear estados comunes
            estado_mapping = {
                'Activa': 'Activo',
                'Active': 'Activo',
                'Inactiva': 'Inactivo',
                'Inactive': 'Inactivo',
            }
            df['estado'] = df['estado'].replace(estado_mapping)
        
        # Remover duplicados por código DANE (mantener el más reciente)
        df = df.dropna(subset=['codigo_dane'])
        df = df.drop_duplicates(subset=['codigo_dane'], keep='last')
        
        # Limpiar coordenadas
        for col in ['latitud', 'longitud']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    @staticmethod
    def _generate_hash(df: pd.DataFrame) -> pd.DataFrame:
        """Genera hash para detección de cambios."""
        df = df.copy()
        
        # Crear string para hash con campos principales
        hash_fields = ['nombre', 'municipio_codigo', 'estado', 'sector', 'zona']
        existing_fields = [f for f in hash_fields if f in df.columns]
        
        def create_hash_string(row):
            values = []
            for field in existing_fields:
                value = str(row.get(field, '')) if pd.notna(row.get(field)) else ''
                values.append(value)
            return '|'.join(values)
        
        df['hash_string'] = df.apply(create_hash_string, axis=1)
        df['updated_hash'] = df['hash_string'].apply(
            lambda s: sha256(s.encode('utf-8')).hexdigest()
        )
        
        # Limpiar columna temporal
        df = df.drop('hash_string', axis=1)
        
        return df


class SupabaseLoader:
    """Cargador de datos en Supabase (Postgres)."""
    
    @staticmethod
    def load_municipios(municipios_data: List[Dict]) -> int:
        """Carga catálogo de municipios."""
        if not municipios_data:
            return 0
        
        try:
            with transaction.atomic():
                municipios_to_create = []
                
                for muni_data in municipios_data:
                    municipio, created = DimMunicipio.objects.get_or_create(
                        codigo=muni_data['codigo'],
                        defaults={
                            'nombre': muni_data['nombre'],
                            'departamento_codigo': muni_data.get('departamento_codigo'),
                            'departamento_nombre': muni_data.get('departamento_nombre'),
                        }
                    )
                    
                    if not created:
                        # Actualizar si existe
                        municipio.nombre = muni_data['nombre']
                        municipio.departamento_codigo = muni_data.get('departamento_codigo')
                        municipio.departamento_nombre = muni_data.get('departamento_nombre')
                        municipio.save()
                
                logger.info(f"Cargados {len(municipios_data)} municipios")
                return len(municipios_data)
                
        except Exception as e:
            logger.error(f"Error cargando municipios: {e}")
            raise
    
    @staticmethod
    def load_instituciones_orm(df: pd.DataFrame, etl_run: ETLRun) -> int:
        """
        Carga instituciones usando Django ORM con bulk operations.
        Método recomendado para datasets medianos con transacciones seguras.
        """
        if df.empty:
            return 0
        
        try:
            # Crear mapeo de municipios
            municipios_map = {
                m.codigo: m.id 
                for m in DimMunicipio.objects.all().only('id', 'codigo')
            }
            
            records_to_create = []
            records_to_update = []
            existing_instituciones = {
                inst.codigo_dane: inst 
                for inst in FactInstitucion.objects.all()
            }
            
            changes_count = 0
            
            with transaction.atomic():
                for _, row in df.iterrows():
                    codigo_dane = row.get('codigo_dane')
                    if not codigo_dane:
                        continue
                    
                    # Preparar datos del registro
                    record_data = {
                        'codigo_dane': codigo_dane,
                        'nombre': row.get('nombre', ''),
                        'municipio_id': municipios_map.get(row.get('municipio_codigo')),
                        'estado': row.get('estado', 'Activo'),
                        'sector': row.get('sector'),
                        'zona': row.get('zona'),
                        'direccion': row.get('direccion'),
                        'telefono': row.get('telefono'),
                        'email': row.get('email'),
                        'latitud': row.get('latitud'),
                        'longitud': row.get('longitud'),
                        'updated_hash': row.get('updated_hash', ''),
                        'source_system': row.get('source_system', 'unknown'),
                    }
                    
                    if codigo_dane in existing_instituciones:
                        # Verificar si cambió
                        existing = existing_instituciones[codigo_dane]
                        if existing.updated_hash != record_data['updated_hash']:
                            # Registrar cambio
                            ChangeLog.objects.create(
                                etl_run=etl_run,
                                table_name='fact_institucion',
                                record_id=codigo_dane,
                                action='update',
                                old_values={'hash': existing.updated_hash},
                                new_values={'hash': record_data['updated_hash']}
                            )
                            
                            # Actualizar registro
                            for field, value in record_data.items():
                                setattr(existing, field, value)
                            records_to_update.append(existing)
                            changes_count += 1
                    else:
                        # Nuevo registro
                        records_to_create.append(FactInstitucion(**record_data))
                        ChangeLog.objects.create(
                            etl_run=etl_run,
                            table_name='fact_institucion',
                            record_id=codigo_dane,
                            action='insert',
                            new_values=record_data
                        )
                        changes_count += 1
                
                # Operaciones bulk
                if records_to_create:
                    FactInstitucion.objects.bulk_create(
                        records_to_create, 
                        batch_size=settings.ETL_BATCH_SIZE,
                        ignore_conflicts=False
                    )
                
                if records_to_update:
                    FactInstitucion.objects.bulk_update(
                        records_to_update,
                        fields=[
                            'nombre', 'municipio', 'estado', 'sector', 'zona',
                            'direccion', 'telefono', 'email', 'latitud', 'longitud',
                            'updated_hash', 'source_system'
                        ],
                        batch_size=settings.ETL_BATCH_SIZE
                    )
                
                total_processed = len(records_to_create) + len(records_to_update)
                logger.info(f"Cargadas {total_processed} instituciones vía ORM")
                
                return total_processed
                
        except Exception as e:
            logger.error(f"Error cargando instituciones vía ORM: {e}")
            raise
    
    @staticmethod
    def load_instituciones_sqlalchemy(df: pd.DataFrame) -> int:
        """
        Carga instituciones usando SQLAlchemy con upsert nativo de PostgreSQL.
        Método recomendado para datasets grandes con mejor rendimiento.
        """
        if df.empty:
            return 0
        
        try:
            # Crear engine de SQLAlchemy
            url = (
                f"postgresql+psycopg://{os.getenv('SUPABASE_DB_USER')}:"
                f"{os.getenv('SUPABASE_DB_PASS')}@{os.getenv('SUPABASE_DB_HOST')}:"
                f"{os.getenv('SUPABASE_DB_PORT')}/{os.getenv('SUPABASE_DB_NAME')}"
                f"?sslmode={os.getenv('SUPABASE_DB_SSLMODE', 'require')}"
            )
            
            engine = create_engine(url, pool_pre_ping=True)
            
            # Preparar datos para carga
            df_load = df.copy()
            
            # Mapear municipios
            municipios_map = {
                m.codigo: m.id 
                for m in DimMunicipio.objects.all().only('id', 'codigo')
            }
            
            df_load['municipio_id'] = df_load['municipio_codigo'].map(municipios_map)
            
            # Seleccionar solo columnas que existen en el modelo
            columns_to_load = [
                'codigo_dane', 'nombre', 'municipio_id', 'estado', 'sector', 'zona',
                'direccion', 'telefono', 'email', 'latitud', 'longitud',
                'updated_hash', 'source_system'
            ]
            
            df_final = df_load[columns_to_load].copy()
            
            # Método de upsert personalizado
            def upsert_method(table, conn, keys, data_iter):
                data = [dict(zip(keys, row)) for row in data_iter]
                
                stmt = insert(table.table).values(data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['codigo_dane'],
                    set_={
                        'nombre': stmt.excluded.nombre,
                        'municipio_id': stmt.excluded.municipio_id,
                        'estado': stmt.excluded.estado,
                        'sector': stmt.excluded.sector,
                        'zona': stmt.excluded.zona,
                        'direccion': stmt.excluded.direccion,
                        'telefono': stmt.excluded.telefono,
                        'email': stmt.excluded.email,
                        'latitud': stmt.excluded.latitud,
                        'longitud': stmt.excluded.longitud,
                        'updated_hash': stmt.excluded.updated_hash,
                        'source_system': stmt.excluded.source_system,
                        'updated_at': 'NOW()',
                    }
                )
                
                result = conn.execute(stmt)
                return result.rowcount
            
            # Ejecutar carga
            rows_affected = df_final.to_sql(
                name='etl_factinstitucion',
                con=engine,
                if_exists='append',
                index=False,
                chunksize=settings.ETL_CHUNK_SIZE,
                method=upsert_method
            )
            
            logger.info(f"Cargadas {len(df_final)} instituciones vía SQLAlchemy")
            return len(df_final)
            
        except Exception as e:
            logger.error(f"Error cargando instituciones vía SQLAlchemy: {e}")
            raise


class ETLOrchestrator:
    """Orquestador principal del proceso ETL."""
    
    def __init__(self):
        self.mysql_extractor = MySQLExtractor()
        self.excel_extractor = ExcelExtractor()
        self.transformer = DataTransformer()
        self.loader = SupabaseLoader()
    
    def run_etl_pipeline(self, excel_a_path: str = None, excel_b_path: str = None) -> ETLRun:
        """
        Ejecuta el pipeline completo de ETL.
        
        Args:
            excel_a_path: Ruta al archivo Excel A
            excel_b_path: Ruta al archivo Excel B
            
        Returns:
            ETLRun con el resultado de la ejecución
        """
        # Crear registro de ejecución
        etl_run = ETLRun.objects.create(
            status='running',
            meta={'excel_a_path': excel_a_path, 'excel_b_path': excel_b_path}
        )
        
        try:
            logger.info(f"Iniciando ETL Run {etl_run.id}")
            
            # 1. Extracción
            logger.info("Fase 1: Extracción de datos")
            
            # Extraer municipios primero (para referencias)
            municipios_data = self.mysql_extractor.extract_municipios()
            municipios_loaded = self.loader.load_municipios(municipios_data)
            
            # Extraer instituciones desde MySQL
            mysql_data = self.mysql_extractor.extract_instituciones()
            
            # Extraer desde Excel (si se proporcionan)
            excel_a_df = pd.DataFrame()
            excel_b_df = pd.DataFrame()
            
            if excel_a_path and os.path.exists(excel_a_path):
                excel_a_df = self.excel_extractor.extract_excel_a(excel_a_path)
            
            if excel_b_path and os.path.exists(excel_b_path):
                excel_b_df = self.excel_extractor.extract_excel_b(excel_b_path)
            
            # 2. Transformación
            logger.info("Fase 2: Transformación y normalización")
            df_transformed = self.transformer.transform_instituciones(
                mysql_data, excel_a_df, excel_b_df
            )
            
            # 3. Carga
            logger.info("Fase 3: Carga en Supabase")
            instituciones_loaded = self.loader.load_instituciones_orm(df_transformed, etl_run)
            
            # Actualizar estado exitoso
            etl_run.status = 'success'
            etl_run.meta.update({
                'municipios_loaded': municipios_loaded,
                'instituciones_loaded': instituciones_loaded,
                'total_records': len(df_transformed),
                'sources': {
                    'mysql': len(mysql_data),
                    'excel_a': len(excel_a_df),
                    'excel_b': len(excel_b_df)
                }
            })
            
            logger.info(f"ETL Run {etl_run.id} completado exitosamente")
            
        except Exception as e:
            logger.error(f"Error en ETL Run {etl_run.id}: {e}")
            etl_run.status = 'failed'
            etl_run.meta.update({'error': str(e)})
            raise
        
        finally:
            etl_run.finished_at = timezone.now() if hasattr(timezone, 'now') else None
            etl_run.save()
        
        return etl_run

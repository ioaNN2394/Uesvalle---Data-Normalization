"""
Extractores de datos: MySQL y Excel
====================================

Sigue estándares:
- Django multi-DB: using('mysql') para acceder a conexión MySQL
- Pandas read_excel con control de tipos y hojas
- Manejo robusto de errores y logging
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import time

import pandas as pd
from django.db import connections, DatabaseError

from . import DataExtractor, ExtractionResult

logger = logging.getLogger('etl.extraction')


class MySQLExtractor(DataExtractor):
    """
    Extrae datos desde MySQL usando la conexión multi-DB de Django.
    
    Uso:
        extractor = MySQLExtractor()
        result = extractor.extract(
            table_name='institutions',
            query='SELECT * FROM institutions WHERE active = 1',
            chunksize=1000
        )
    """
    
    def __init__(self, db_alias: str = 'mysql'):
        """
        Args:
            db_alias: Alias de la conexión en settings.DATABASES (default: 'mysql')
        """
        self.db_alias = db_alias
        self.connection = None
    
    def extract(self, 
                table_name: str,
                query: Optional[str] = None,
                chunksize: Optional[int] = None,
                **kwargs) -> ExtractionResult:
        """
        Extrae datos desde MySQL.
        
        Args:
            table_name: Nombre de la tabla (para metadatos)
            query: Consulta SQL custom. Si no se proporciona, extrae toda la tabla
            chunksize: Tamaño de chunk para grandes consultas (reduce memoria)
            **kwargs: Argumentos adicionales (no usados ahora)
        
        Returns:
            ExtractionResult con el DataFrame
        
        Raises:
            DatabaseError: Si hay problema de conexión
            Exception: Si la consulta falla
        """
        start_time = time.time()
        
        try:
            # Validar conexión
            self._validate_connection()
            
            # Determinar consulta
            if not query:
                query = f"SELECT * FROM {table_name}"
            
            logger.info(f"Extrayendo desde {self.db_alias}.{table_name}...")
            logger.debug(f"Consulta: {query}")
            
            # Usar django-db-utils para obtener URL de conexión
            db_config = self._get_db_config()
            
            # Leer con pandas desde conexión de Django
            # Opción 1: Usar psycopg2/mysql driver directo
            # Opción 2: Usar SQLAlchemy (requiere sqlalchemy package)
            
            # Implementamos con conexión nativa de Django
            connection = connections[self.db_alias]
            
            # Para MySQL/psycopg, usar read_sql_query
            try:
                # Si tienes sqlalchemy
                from sqlalchemy import create_engine
                engine = self._create_sqlalchemy_engine()
                
                if chunksize:
                    # Leer en chunks para grandes volúmenes
                    chunks = []
                    for chunk_df in pd.read_sql_query(query, con=engine, chunksize=chunksize):
                        chunks.append(chunk_df)
                    df = pd.concat(chunks, ignore_index=True)
                else:
                    df = pd.read_sql_query(query, con=engine)
                
                logger.info(f"✓ Extracción exitosa: {len(df)} registros")
                
            except ImportError:
                # Fallback: usar read_sql con conexión nativa
                # Esto funciona con psycopg2 backend
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    df = pd.DataFrame(rows, columns=columns)
                
                logger.info(f"✓ Extracción exitosa (fallback): {len(df)} registros")
            
            # Calcular métricas
            extraction_time = time.time() - start_time
            
            # Crear resultado
            result = ExtractionResult(
                source=self.db_alias,
                table_name=table_name,
                dataframe=df,
                records_count=len(df),
                extraction_time=extraction_time,
                metadata={
                    'query': query,
                    'chunksize': chunksize,
                    'columns': list(df.columns),
                    'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            return result
            
        except DatabaseError as e:
            logger.error(f"❌ Error de conexión a {self.db_alias}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error en extracción: {e}")
            raise
    
    def _validate_connection(self) -> bool:
        """Valida que la conexión esté disponible."""
        try:
            connection = connections[self.db_alias]
            connection.ensure_connection()
            logger.debug(f"✓ Conexión a {self.db_alias} verificada")
            return True
        except Exception as e:
            logger.error(f"❌ No se pudo conectar a {self.db_alias}: {e}")
            raise
    
    def _get_db_config(self) -> Dict[str, Any]:
        """Obtiene configuración de la BD desde Django settings."""
        from django.conf import settings
        return settings.DATABASES.get(self.db_alias, {})
    
    def _create_sqlalchemy_engine(self):
        """Crea motor SQLAlchemy desde config de Django."""
        from sqlalchemy import create_engine
        
        config = self._get_db_config()
        
        # Construir URL según ENGINE
        engine_type = config.get('ENGINE', '')
        
        if 'mysql' in engine_type:
            # mysql://usuario:contraseña@host:puerto/base
            url = (f"mysql+pymysql://{config['USER']}:{config['PASSWORD']}"
                   f"@{config['HOST']}:{config.get('PORT', 3306)}/{config['NAME']}")
        elif 'postgresql' in engine_type:
            # postgresql://usuario:contraseña@host:puerto/base
            url = (f"postgresql://{config['USER']}:{config['PASSWORD']}"
                   f"@{config['HOST']}:{config.get('PORT', 5432)}/{config['NAME']}")
        else:
            raise ValueError(f"Engine no soportado: {engine_type}")
        
        return create_engine(url, echo=False)


class ExcelExtractor(DataExtractor):
    """
    Extrae datos desde archivos Excel (.xlsx, .xls).
    
    Características:
    - Lee múltiples hojas
    - Control de tipos de datos
    - Validación de esquema
    - Soporte para fechas y números
    
    Uso:
        extractor = ExcelExtractor()
        result = extractor.extract(
            file_path='/ruta/al/archivo.xlsx',
            sheet_name='Datos',
            header_row=0,
            dtype_hints={'date_col': 'datetime', 'id_col': 'string'}
        )
    """
    
    def extract(self,
                file_path: str,
                sheet_name: str = 0,
                header_row: int = 0,
                skiprows: Optional[List[int]] = None,
                dtype_hints: Optional[Dict[str, str]] = None,
                **kwargs) -> ExtractionResult:
        """
        Extrae datos desde Excel.
        
        Args:
            file_path: Ruta al archivo Excel
            sheet_name: Nombre o índice de la hoja (default: primera hoja)
            header_row: Fila con encabezados (default: 0)
            skiprows: Filas a omitir (ej: [0, 1] para metadatos)
            dtype_hints: Hints de tipos {columna: tipo}
            **kwargs: Args adicionales para pd.read_excel
        
        Returns:
            ExtractionResult
        """
        start_time = time.time()
        
        try:
            logger.info(f"Extrayendo desde Excel: {file_path}")
            logger.debug(f"Hoja: {sheet_name}, Header row: {header_row}")
            
            # Construir parámetros de read_excel
            read_params = {
                'sheet_name': sheet_name,
                'header': header_row,
                'skiprows': skiprows,
                **kwargs
            }
            
            # Leer Excel
            df = pd.read_excel(file_path, **read_params)
            
            logger.debug(f"Columnas: {list(df.columns)}")
            logger.debug(f"Shape: {df.shape}")
            
            # Aplicar hints de tipo
            if dtype_hints:
                df = self._apply_dtype_hints(df, dtype_hints)
            
            # Limpieza básica
            df = self._clean_dataframe(df)
            
            # Calcular métricas
            extraction_time = time.time() - start_time
            
            result = ExtractionResult(
                source='excel',
                table_name=f"{file_path}#{sheet_name}",
                dataframe=df,
                records_count=len(df),
                extraction_time=extraction_time,
                metadata={
                    'file_path': file_path,
                    'sheet_name': str(sheet_name),
                    'columns': list(df.columns),
                    'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                    'shape': df.shape,
                    'null_counts': df.isnull().sum().to_dict(),
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info(f"✓ Extracción exitosa: {len(df)} registros")
            return result
            
        except FileNotFoundError:
            logger.error(f"❌ Archivo no encontrado: {file_path}")
            raise
        except Exception as e:
            logger.error(f"❌ Error en extracción Excel: {e}")
            raise
    
    @staticmethod
    def _apply_dtype_hints(df: pd.DataFrame, dtype_hints: Dict[str, str]) -> pd.DataFrame:
        """Aplica hints de tipos de datos."""
        from . import TypeConverter
        
        for col, type_hint in dtype_hints.items():
            if col in df.columns:
                converted, error = TypeConverter.convert_column(df[col], type_hint)
                if error:
                    logger.warning(f"Columna {col}: {error}")
                else:
                    df[col] = converted
        
        return df
    
    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Limpieza básica del DataFrame."""
        # Eliminar filas completamente vacías
        df = df.dropna(how='all')
        
        # Eliminar espacios en blanco en encabezados
        df.columns = df.columns.str.strip()
        
        # Eliminar espacios en columnas de texto
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].astype(str).str.strip()
        
        return df
    
    @staticmethod
    def get_sheet_names(file_path: str) -> List[str]:
        """Obtiene lista de hojas en un Excel."""
        try:
            xl_file = pd.ExcelFile(file_path)
            return xl_file.sheet_names
        except Exception as e:
            logger.error(f"Error obteniendo hojas: {e}")
            raise


class MultiSourceExtractor:
    """
    Orquesta extracción de múltiples fuentes (MySQL + Excel).
    
    Combina datos usando merge/join.
    """
    
    def __init__(self):
        self.mysql_extractor = MySQLExtractor()
        self.excel_extractor = ExcelExtractor()
    
    def extract_and_merge(self,
                         mysql_query: str,
                         excel_file: str,
                         excel_sheet: str = 0,
                         merge_key: Optional[str] = None,
                         how: str = 'outer') -> pd.DataFrame:
        """
        Extrae de MySQL y Excel y los une.
        
        Args:
            mysql_query: Consulta SQL
            excel_file: Ruta archivo Excel
            excel_sheet: Hoja de Excel
            merge_key: Clave para el merge (mismo nombre en ambas fuentes)
            how: Tipo de join ('inner', 'outer', 'left', 'right')
        
        Returns:
            DataFrame unificado
        """
        logger.info("Iniciando extracción multi-fuente...")
        
        # Extracción MySQL
        mysql_result = self.mysql_extractor.extract(
            table_name='source_table',
            query=mysql_query
        )
        
        # Extracción Excel
        excel_result = self.excel_extractor.extract(
            file_path=excel_file,
            sheet_name=excel_sheet
        )
        
        mysql_df = mysql_result.dataframe
        excel_df = excel_result.dataframe
        
        # Merge
        if merge_key and merge_key in mysql_df.columns and merge_key in excel_df.columns:
            logger.info(f"Mergeando en clave: {merge_key}")
            merged_df = pd.merge(mysql_df, excel_df, on=merge_key, how=how)
        else:
            # Concatenar si no hay clave
            logger.info("Concatenando DataFrames (sin clave de merge)")
            merged_df = pd.concat([mysql_df, excel_df], ignore_index=True)
        
        logger.info(f"✓ Merge completado: {len(merged_df)} registros totales")
        return merged_df


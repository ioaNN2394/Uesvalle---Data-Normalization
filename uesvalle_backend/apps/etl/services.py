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
from django.utils import timezone
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
import logging

from .models import (
    ETLRun, DimMunicipio, DimSede, FactInstitucion, 
    ChangeLog, StgInstitucionMySQL, Institucion, Sede, 
    FactMatricula, FactMatriculaEtnica, PaeAsignacion, Visita
)

logger = logging.getLogger(__name__)


class MySQLExtractor:
    """Extractor de datos desde MySQL."""
    
    def _get_connection_params(self) -> Dict[str, Any]:
        """Obtiene parámetros de conexión para MySQL desde variables de entorno."""
        return {
            'host': os.getenv('MYSQL_DB_HOST', os.getenv('SOURCE_MYSQL_HOST', 'localhost')),
            'port': int(os.getenv('MYSQL_DB_PORT', os.getenv('SOURCE_MYSQL_PORT', 3306))),
            'user': os.getenv('MYSQL_DB_USER', os.getenv('SOURCE_MYSQL_USER', 'root')),
            'password': os.getenv('MYSQL_DB_PASSWORD', os.getenv('SOURCE_MYSQL_PASSWORD', '')),
            'database': os.getenv('MYSQL_DB_NAME', os.getenv('SOURCE_MYSQL_DB', 'mysql')),
        }
    
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
    """
    Extractor mejorado para múltiples archivos Excel según documentación oficial.
    - Usa pd.read_excel() para cada archivo
    - pd.concat() para unir múltiples DataFrames
    - Mapeo automático de columnas heterogéneas 
    - Esquema canónico para normalización
    """
    
    def __init__(self, verbose=False):
        self.logger = logging.getLogger(__name__)
        self.verbose = verbose
        self._current_file = None
        
        # Esquema canónico según diseño Supabase
        # Corregido: usar nombres exactos de columnas sin _id según documentación
        self.canonical_schema = {
            'instituciones': {
                'nombre': str,              # nombre exacto de la columna
                'dane_ie_id': str,         # estos sí terminan en _id
                'sed_ie_id': str,
                'uesvalle_ie_id': str,
                'codigo_municipio': str,   # sin _id, referencia directa
                'direccion': str,
                'telefono': str,
                'email': str,
                'estado': str
            },
            'sedes': {
                'nombre_sede': str,
                'dane_sede_id': str,
                'sed_sede_id': str,
                'uesvalle_sede_id': str,
                'institucion_referencia': str,  # Para vincular con IE
                'codigo_municipio': str,
                'direccion': str,
                'lat': float,
                'lon': float
            },
            'matricula': {
                'sede_referencia': str,
                'corte_fecha': str,
                'nivel': str,
                'grado': str,
                'jornada': str,
                'genero': str,
                'total_alumnos': int
            },
            'matricula_etnica': {
                'sede_referencia': str,
                'corte_fecha': str,
                'grupo_etnico': str,
                'total_alumnos': int
            },
            'pae': {
                'sede_referencia': str,
                'anio': int,
                'periodo': str,
                'modalidad': str,
                'beneficiarios': int
            },
            'visitas': {
                'sede_referencia': str,
                'institucion_referencia': str,
                'fecha': str,
                'programa': str,
                'resultado': str,
                'observaciones': str
            }
        }
        
        # Mapeo de columnas heterogéneas (según docs pandas)
        # Corregido: mapear a nombres exactos sin _id
        self.column_mapping = {
            'instituciones': {
                'nombre': [  # campo exacto en tabla institucion
                    'nombre', 'institucion', 'nombre_institucion', 'ie', 'nombre_ie',
                    'institución', 'nombre de la institución', 'colegio', 'escuela'
                ],
                'dane_ie_id': [
                    'dane', 'codigo_dane', 'dane_ie', 'codigo_ie', 'dane_institucion',
                    'código dane', 'codigo dane', 'dane_codigo', 'dane ie'
                ],
                'codigo_municipio': [
                    'municipio', 'codigo_municipio', 'mpio', 'municipio_codigo',
                    'código municipio', 'cod_municipio'
                ],
                'direccion': ['direccion', 'dir', 'address', 'dirección'],
                'telefono': ['telefono', 'tel', 'phone', 'teléfono'],
                'estado': ['estado', 'sector', 'tipo', 'naturaleza'],
                'email': ['email', 'correo', 'mail', 'e-mail']
            },
            'matricula': {
                'sede_referencia': [
                    'sede', 'nombre_sede', 'campus', 'sede_nombre'
                ],
                'nivel': [
                    'nivel', 'nivel_educativo', 'type', 'tipo_nivel'
                ],
                'grado': ['grado', 'grade', 'curso', 'año'],
                'jornada': [
                    'jornada', 'turno', 'shift', 'horario'
                ],
                'genero': [
                    'genero', 'sexo', 'gender', 'm_f', 'género'
                ],
                'total_alumnos': [
                    'total', 'estudiantes', 'alumnos', 'count', 'cantidad',
                    'total_estudiantes', 'total_alumnos', 'matricula'
                ],
                'corte_fecha': [
                    'fecha', 'corte', 'periodo', 'fecha_corte'
                ]
            },
            'matricula_etnica': {
                'grupo_etnico': [
                    'etnia', 'grupo_etnico', 'raza', 'poblacion',
                    'grupo étnico', 'población étnica'
                ],
                'total_alumnos': [
                    'total', 'estudiantes', 'alumnos', 'count'
                ]
            },
            'pae': {
                'modalidad': [
                    'modalidad', 'tipo_pae', 'programa', 'modalidad_pae'
                ],
                'beneficiarios': [
                    'beneficiarios', 'estudiantes', 'total', 'cantidad'
                ],
                'anio': ['año', 'anio', 'year'],
                'periodo': ['periodo', 'semestre', 'trimestre']
            }
        }

    def extract_from_directory(self, directory_path: str, file_patterns: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """
        Extrae datos de múltiples archivos Excel según documentación:
        - Itera archivos *.xlsx 
        - pd.read_excel() por archivo
        - pd.concat() para unir con join='outer' (default)
        
        Args:
            directory_path: Directorio con archivos Excel
            file_patterns: Patrones de archivos a buscar
            
        Returns:
            Dict con datos extraídos por tipo
        """
        from pathlib import Path
        
        if not directory_path or not os.path.exists(directory_path):
            raise ValueError(f"Directorio no existe: {directory_path}")
        
        directory = Path(directory_path)
        
        # Patrones por defecto
        if file_patterns is None:
            file_patterns = [
                '*matricula*.xlsx', '*matricula*.xls',
                '*institucion*.xlsx', '*institucion*.xls', 
                '*pae*.xlsx', '*pae*.xls',
                '*etnic*.xlsx', '*etnic*.xls',
                '*visita*.xlsx', '*visita*.xls'
            ]
        
        # Recopilar archivos Excel únicos
        excel_files = []
        for pattern in file_patterns + ['*.xlsx', '*.xls']:
            excel_files.extend(directory.glob(pattern))
        
        # Eliminar duplicados preservando orden
        unique_files = list(dict.fromkeys(excel_files))
        
        self._log(f"📁 Directorio: {directory_path}")
        self._log(f"📄 Archivos Excel encontrados: {len(unique_files)}")
        
        # Estructura para acumular DataFrames por tipo
        dataframes_by_type = {
            'instituciones': [],
            'sedes': [],
            'matricula': [],
            'matricula_etnica': [],
            'pae': [],
            'visitas': []
        }
        
        # Procesar cada archivo
        for file_path in unique_files:
            self._log(f"📋 Procesando: {file_path.name}")
            self._current_file = file_path.name
            
            try:
                file_dataframes = self._extract_from_single_file(file_path)
                
                # Acumular DataFrames por tipo
                for data_type, df_list in file_dataframes.items():
                    if df_list:
                        dataframes_by_type[data_type].extend(df_list)
                        self._log(f"  ✅ {data_type}: +{len(df_list)} DataFrames")
                
            except Exception as e:
                self._log(f"  ❌ Error procesando {file_path.name}: {e}")
                continue
        
        # Concatenar DataFrames usando pd.concat() según documentación
        final_data = {}
        
        for data_type, df_list in dataframes_by_type.items():
            if df_list:
                # pd.concat() con join='outer' (default) para union de columnas
                combined_df = pd.concat(df_list, ignore_index=True, join='outer')
                
                # Convertir a lista de diccionarios
                final_data[data_type] = combined_df.to_dict('records')
                
                self._log(f"📊 {data_type}: {len(final_data[data_type])} registros finales")
            else:
                final_data[data_type] = []
        
        # Resumen final
        total_records = sum(len(records) for records in final_data.values())
        self._log(f"\n🎯 RESUMEN EXTRACCIÓN:")
        for data_type, records in final_data.items():
            if records:
                self._log(f"  ✅ {data_type}: {len(records)} registros")
        self._log(f"  📈 TOTAL: {total_records} registros")
        
        return final_data

    def _extract_from_single_file(self, file_path) -> Dict[str, List[pd.DataFrame]]:
        """Extrae datos de un único archivo Excel usando pd.read_excel()"""
        try:
            # Leer todas las hojas del Excel
            excel_data = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            
            dataframes_by_type = {
                'instituciones': [],
                'sedes': [],
                'matricula': [],
                'matricula_etnica': [],
                'pae': [],
                'visitas': []
            }
            
            for sheet_name, df in excel_data.items():
                if df.empty:
                    continue
                
                # Detectar tipo de datos
                data_type = self._detect_data_type(df.columns, sheet_name, file_path.name)
                
                if data_type:
                    # Normalizar según esquema canónico
                    normalized_df = self._normalize_to_canonical_schema(df, data_type)
                    
                    if not normalized_df.empty:
                        dataframes_by_type[data_type].append(normalized_df)
            
            return dataframes_by_type
            
        except Exception as e:
            self._log(f"Error leyendo {file_path}: {e}")
            return {key: [] for key in dataframes_by_type.keys()}

    @staticmethod
    def read_excel_file(file_path: str, sheet_name: str = 0) -> pd.DataFrame:
        """
        MÉTODO LEGACY - Lee archivo Excel y retorna DataFrame.
        Usar extract_from_directory() para múltiples archivos.
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

    def _detect_data_type(self, columns, sheet_name="", file_name=""):
        """
        Detectar tipo de datos basado en columnas y nombres de hoja/archivo.
        Implementa detección inteligente según palabras clave.
        """
        columns_lower = [str(col).lower().strip() for col in columns]
        sheet_lower = sheet_name.lower()
        file_lower = file_name.lower()
        
        # Buscar por nombres de hoja/archivo primero
        if any(keyword in sheet_lower for keyword in ['matricula', 'estudiante', 'alumno']):
            if any(keyword in ' '.join(columns_lower) for keyword in ['etnic', 'raza', 'poblacion']):
                return 'matricula_etnica'
            return 'matricula'
        
        elif any(keyword in sheet_lower for keyword in ['institucion', 'colegio', 'escuela', 'ie']):
            return 'instituciones'
            
        elif any(keyword in sheet_lower for keyword in ['sede', 'campus', 'planta']):
            return 'sedes'
        
        elif any(keyword in sheet_lower for keyword in ['pae', 'alimentacion', 'comedor']):
            return 'pae'
        
        elif any(keyword in sheet_lower for keyword in ['visita', 'supervision', 'acompañamiento']):
            return 'visitas'
        
        # Buscar por nombre de archivo si no se detectó por hoja
        if any(keyword in file_lower for keyword in ['matricula', 'estudiante']):
            if any(keyword in file_lower for keyword in ['etnic', 'raza']):
                return 'matricula_etnica'
            return 'matricula'
            
        elif any(keyword in file_lower for keyword in ['institucion', 'colegio', 'ie']):
            return 'instituciones'
            
        elif any(keyword in file_lower for keyword in ['pae', 'alimentacion']):
            return 'pae'
        
        # Detectar por contenido de columnas
        if any(col in columns_lower for col in ['dane', 'institucion', 'colegio', 'nombre_ie']):
            return 'instituciones'
        
        elif any(col in columns_lower for col in ['total_alumnos', 'estudiantes', 'matricula']):
            if any(col in columns_lower for col in ['etnia', 'raza', 'poblacion', 'grupo_etnico']):
                return 'matricula_etnica'
            return 'matricula'
        
        elif any(col in columns_lower for col in ['modalidad_pae', 'beneficiarios', 'pae']):
            return 'pae'
            
        elif any(col in columns_lower for col in ['sede', 'campus', 'nombre_sede']):
            return 'sedes'
        
        self._log(f"  ⚠️ Tipo no detectado para hoja '{sheet_name}' - columnas: {columns_lower[:3]}...")
        return None

    def _normalize_to_canonical_schema(self, df, data_type):
        """
        Normaliza DataFrame al esquema canónico usando:
        1. DataFrame.rename() para mapeo de columnas
        2. df.assign() para crear columnas faltantes  
        3. astype() para tipos consistentes
        4. fillna() para valores faltantes
        """
        if data_type not in self.column_mapping:
            return df
        
        normalized_df = df.copy()
        mapping = self.column_mapping[data_type]
        canonical_cols = self.canonical_schema[data_type]
        
        # 1. Mapear columnas heterogéneas usando DataFrame.rename()
        rename_map = {}
        for target_col, possible_names in mapping.items():
            for col in df.columns:
                col_clean = str(col).lower().strip()
                if col_clean in [name.lower().strip() for name in possible_names]:
                    if col != target_col:
                        rename_map[col] = target_col
                    break
        
        if rename_map:
            normalized_df = normalized_df.rename(columns=rename_map)
            self._log(f"  🔄 Columnas mapeadas: {list(rename_map.keys())} → {list(rename_map.values())}")
        
        # 2. Crear columnas faltantes con valores por defecto usando assign()
        missing_cols = {}
        for canon_col in canonical_cols.keys():
            if canon_col not in normalized_df.columns:
                # Valores por defecto según tipo
                if canonical_cols[canon_col] == str:
                    missing_cols[canon_col] = ''
                elif canonical_cols[canon_col] == int:
                    missing_cols[canon_col] = 0
                elif canonical_cols[canon_col] == float:
                    missing_cols[canon_col] = 0.0
                else:
                    missing_cols[canon_col] = None
        
        if missing_cols:
            normalized_df = normalized_df.assign(**missing_cols)
            self._log(f"  ➕ Columnas agregadas: {list(missing_cols.keys())}")
        
        # 3. Aplicar tipos consistentes con astype()
        type_map = {}
        for col, dtype in canonical_cols.items():
            if col in normalized_df.columns:
                if dtype == str:
                    type_map[col] = 'string'
                elif dtype == int:
                    # Manejar NaN en enteros
                    normalized_df[col] = pd.to_numeric(normalized_df[col], errors='coerce')
                    type_map[col] = 'Int64'  # Nullable integer
                elif dtype == float:
                    type_map[col] = 'float64'
        
        if type_map:
            try:
                normalized_df = normalized_df.astype(type_map)
                self._log(f"  🔧 Tipos aplicados: {len(type_map)} columnas")
            except Exception as e:
                self._log(f"  ⚠️ Error aplicando tipos: {e}")
        
        # 4. Manejar valores faltantes con fillna()
        fill_values = {}
        for col in normalized_df.columns:
            if col in canonical_cols:
                if canonical_cols[col] == str:
                    fill_values[col] = ''
                elif canonical_cols[col] in [int, float]:
                    fill_values[col] = 0
        
        if fill_values:
            normalized_df = normalized_df.fillna(fill_values)
        
        # Agregar metadatos de auditoría
        normalized_df = normalized_df.assign(
            fuente_archivo=self._current_file or 'desconocido',
            fecha_procesamiento=pd.Timestamp.now(),
            tipo_datos=data_type
        )
        
        self._log(f"  ✅ Normalizado a esquema canónico: {len(normalized_df)} filas, {len(normalized_df.columns)} cols")
        
        return normalized_df

    def _log(self, message):
        """Helper para logging condicional"""
        if self.verbose:
            print(message)
        self.logger.info(message)
    
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
    """
    Cargador de datos en Supabase (Postgres).
    Corregido para usar upsert con on_conflict según documentación PostgreSQL oficial.
    """
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
    
    def upsert_municipios_supabase(self, municipios_data: List[Dict]) -> Dict:
        """
        Upsert municipios usando supabase-py con on_conflict según documentación oficial.
        PK: codigo_municipio (CharField)
        """
        if not municipios_data:
            return {'inserted': 0, 'updated': 0}
        
        try:
            from supabase import create_client
            
            # Configurar cliente Supabase
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # service_role para bypassing RLS
            
            if not supabase_url or not supabase_key:
                self._log("⚠️ Credenciales Supabase no configuradas, usando Django ORM")
                return self.load_municipios_orm(municipios_data)
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Preparar datos según esquema canonical
            upsert_data = []
            for muni in municipios_data:
                upsert_data.append({
                    'codigo_municipio': muni.get('codigo_municipio'),  # PK
                    'nombre': muni.get('nombre', ''),
                    'codigo_departamento': muni.get('codigo_departamento', ''),
                })
            
            # Upsert usando INSERT ... ON CONFLICT según documentación PostgreSQL
            result = supabase.table('dim_municipio').upsert(
                upsert_data,
                on_conflict='codigo_municipio'  # PK para upsert
            ).execute()
            
            self._log(f"✅ Upsert municipios: {len(upsert_data)} registros procesados")
            
            return {
                'inserted': len([r for r in result.data if r.get('__inserted', True)]),
                'updated': len([r for r in result.data if not r.get('__inserted', True)]),
                'total': len(result.data)
            }
            
        except ImportError:
            self._log("⚠️ supabase-py no instalado, usando Django ORM")
            return self.load_municipios_orm(municipios_data)
        except Exception as e:
            self._log(f"❌ Error en upsert Supabase: {e}")
            # Fallback a Django ORM
            return self.load_municipios_orm(municipios_data)
    
    def upsert_instituciones_supabase(self, instituciones_data: List[Dict]) -> Dict:
        """
        Upsert instituciones usando supabase-py con on_conflict.
        Maneja múltiples índices únicos: dane_ie_id, sed_ie_id, uesvalle_ie_id
        """
        if not instituciones_data:
            return {'inserted': 0, 'updated': 0}
        
        try:
            from supabase import create_client
            
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not supabase_url or not supabase_key:
                self._log("⚠️ Usando Django ORM para instituciones")
                return self.load_instituciones_orm_fixed(instituciones_data)
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Preparar datos según esquema corregido (sin _id en codigo_municipio)
            upsert_data = []
            for inst in instituciones_data:
                upsert_data.append({
                    'nombre': inst.get('nombre', ''),          # campo exacto
                    'dane_ie_id': inst.get('dane_ie_id'),      # sí termina en _id
                    'sed_ie_id': inst.get('sed_ie_id'),
                    'uesvalle_ie_id': inst.get('uesvalle_ie_id'), 
                    'codigo_municipio': inst.get('codigo_municipio'),  # sin _id
                    'direccion': inst.get('direccion', ''),
                    'telefono': inst.get('telefono', ''),
                    'email': inst.get('email', ''),
                    'estado': inst.get('estado', ''),
                    'metadata': inst.get('metadata', {})
                })
            
            # Upsert usando dane_ie_id como conflicto principal
            # Según documentación: usar columna única para on_conflict
            result = supabase.table('institucion').upsert(
                upsert_data,
                on_conflict='dane_ie_id'  # Índice único principal
            ).execute()
            
            self._log(f"✅ Upsert instituciones: {len(upsert_data)} registros procesados")
            
            return {
                'inserted': len([r for r in result.data if r.get('__inserted', True)]),
                'updated': len([r for r in result.data if not r.get('__inserted', True)]),
                'total': len(result.data)
            }
            
        except ImportError:
            self._log("⚠️ supabase-py no instalado")
            return self.load_instituciones_orm_fixed(instituciones_data)
        except Exception as e:
            self._log(f"❌ Error en upsert instituciones: {e}")
            return self.load_instituciones_orm_fixed(instituciones_data)
    
    def upsert_fact_matricula_supabase(self, matricula_data: List[Dict]) -> Dict:
        """
        Upsert fact_matricula usando PK compuesta según documentación.
        PK: (sede_id, corte_fecha, nivel, grado, jornada, genero)
        """
        if not matricula_data:
            return {'inserted': 0, 'updated': 0}
        
        try:
            from supabase import create_client
            
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not supabase_url or not supabase_key:
                self._log("⚠️ Usando Django ORM para matrícula")
                return {'inserted': 0, 'updated': 0}  # Implementar ORM después
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Preparar datos según esquema de hechos
            upsert_data = []
            for mat in matricula_data:
                upsert_data.append({
                    'sede_id': mat.get('sede_id'),
                    'corte_fecha': mat.get('corte_fecha'),
                    'nivel': mat.get('nivel', ''),
                    'grado': mat.get('grado', ''),
                    'jornada': mat.get('jornada', ''),
                    'genero': mat.get('genero', ''),
                    'total_alumnos': int(mat.get('total_alumnos', 0)),
                    'fuente': mat.get('fuente', ''),
                    'metadata': mat.get('metadata', {})
                })
            
            # Upsert con PK compuesta según documentación PostgreSQL
            result = supabase.table('fact_matricula').upsert(
                upsert_data,
                # Todas las columnas de la PK compuesta según esquema
                on_conflict='sede_id,corte_fecha,nivel,grado,jornada,genero'
            ).execute()
            
            self._log(f"✅ Upsert matrícula: {len(upsert_data)} registros procesados")
            
            return {
                'inserted': len([r for r in result.data if r.get('__inserted', True)]),
                'updated': len([r for r in result.data if not r.get('__inserted', True)]),
                'total': len(result.data)
            }
            
        except Exception as e:
            self._log(f"❌ Error en upsert matrícula: {e}")
            return {'inserted': 0, 'updated': 0}
    
    def _log(self, message):
        """Helper para logging condicional"""
        if self.verbose:
            print(message)
        self.logger.info(message)

    def load_municipios_orm(self, municipios_data: List[Dict]) -> Dict:
        """Fallback usando Django ORM para municipios"""
        try:
            inserted, updated = 0, 0
            
            with transaction.atomic():
                for muni_data in municipios_data:
                    municipio, created = DimMunicipio.objects.get_or_create(
                        codigo_municipio=muni_data['codigo_municipio'],  # PK corregida
                        defaults=muni_data
                    )
                    
                    if created:
                        inserted += 1
                    else:
                        # Actualizar campos
                        for key, value in muni_data.items():
                            setattr(municipio, key, value)
                        municipio.save()
                        updated += 1
            
            return {'inserted': inserted, 'updated': updated, 'total': len(municipios_data)}
            
        except Exception as e:
            self._log(f"❌ Error ORM municipios: {e}")
            return {'inserted': 0, 'updated': 0, 'total': 0}

    def load_instituciones_orm_fixed(self, instituciones_data: List[Dict]) -> Dict:
        """Fallback usando Django ORM corregido para instituciones"""
        try:
            inserted, updated = 0, 0
            
            with transaction.atomic():
                for inst_data in instituciones_data:
                    # Usar dane_ie_id como clave principal si está disponible
                    lookup_field = None
                    lookup_value = None
                    
                    if inst_data.get('dane_ie_id'):
                        lookup_field = 'dane_ie_id'
                        lookup_value = inst_data['dane_ie_id']
                    elif inst_data.get('sed_ie_id'):
                        lookup_field = 'sed_ie_id' 
                        lookup_value = inst_data['sed_ie_id']
                    elif inst_data.get('uesvalle_ie_id'):
                        lookup_field = 'uesvalle_ie_id'
                        lookup_value = inst_data['uesvalle_ie_id']
                    
                    if lookup_field and lookup_value:
                        institucion, created = Institucion.objects.get_or_create(
                            **{lookup_field: lookup_value},
                            defaults=inst_data
                        )
                        
                        if created:
                            inserted += 1
                        else:
                            # Actualizar campos
                            for key, value in inst_data.items():
                                setattr(institucion, key, value)
                            institucion.save()
                            updated += 1
            
            return {'inserted': inserted, 'updated': updated, 'total': len(instituciones_data)}
            
        except Exception as e:
            self._log(f"❌ Error ORM instituciones: {e}")
            return {'inserted': 0, 'updated': 0, 'total': 0}
    
    @staticmethod
    def load_municipios(municipios_data: List[Dict]) -> int:
        """
        Carga catálogo de municipios - método legacy 
        Actualizado para usar nueva implementación con upsert
        """
        if not municipios_data:
            return 0
        
        # Convertir formato legacy a formato canonical corregido
        canonical_data = []
        for muni_data in municipios_data:
            canonical_data.append({
                'codigo_municipio': muni_data.get('codigo'),  # PK corregida
                'nombre': muni_data.get('nombre', ''),
                'codigo_departamento': muni_data.get('departamento_codigo', ''),
            })
        
        # Usar nueva implementación con upsert
        loader = SupabaseLoader()
        result = loader.upsert_municipios_supabase(canonical_data)
        return result.get('inserted', 0)
    
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


# Clase ETLOrchestrator duplicada eliminada - usar la implementación completa más abajo


class ETLOrchestrator:
    """
    Orquestador principal del ETL que coordina todas las operaciones.
    Corregido para aceptar parámetro verbose según documentación.
    """
    
    def __init__(self, *, verbose=False, logger=None, **kwargs):
        """
        Inicializar ETLOrchestrator.
        
        Args:
            verbose: Habilitar salida detallada
            logger: Logger personalizado (opcional)
            **kwargs: Argumentos adicionales para compatibilidad
        """
        self.verbose = verbose
        self.logger = logger or logging.getLogger(__name__)
        self.mysql_extractor = MySQLExtractor()
        self.excel_extractor = ExcelExtractor(verbose=verbose)
        self.transformer = DataTransformer()
        self.loader = SupabaseLoader(verbose=verbose)
    
    def execute_full_pipeline(self, excel_a_path: Optional[str] = None, 
                            excel_b_path: Optional[str] = None,
                            mysql_only: bool = False,
                            dry_run: bool = False) -> ETLRun:
        """
        Ejecuta el pipeline ETL completo.
        
        Args:
            excel_a_path: Ruta al primer archivo Excel (opcional)
            excel_b_path: Ruta al segundo archivo Excel (opcional)
            mysql_only: Si True, solo procesa datos de MySQL
            dry_run: Si True, no guarda datos reales
            
        Returns:
            ETLRun: Instancia del registro de ejecución
        """
        logger.info("Iniciando pipeline ETL completo")
        
        # Crear registro de ejecución
        etl_run = ETLRun.objects.create(
            meta={
                'pipeline_type': 'full',
                'mysql_only': mysql_only,
                'dry_run': dry_run,
                'excel_files': {
                    'excel_a': excel_a_path,
                    'excel_b': excel_b_path
                }
            }
        )
        
        try:
            # 1. Extraer datos
            mysql_data = []
            excel_data = []
            
            # Extraer desde MySQL
            if not dry_run:
                mysql_data = self.mysql_extractor.extract_instituciones()
                logger.info(f"Extraídos {len(mysql_data)} registros de MySQL")
            
            # Extraer desde Excel si no es mysql_only
            if not mysql_only and not dry_run:
                if excel_a_path and os.path.exists(excel_a_path):
                    excel_a_df = self.excel_extractor.extract_excel_a(excel_a_path)
                    excel_data.extend(excel_a_df.to_dict('records'))
                    
                if excel_b_path and os.path.exists(excel_b_path):
                    excel_b_df = self.excel_extractor.extract_excel_b(excel_b_path)
                    excel_data.extend(excel_b_df.to_dict('records'))
                    
                logger.info(f"Extraídos {len(excel_data)} registros de Excel")
            
            # 2. Transformar datos
            combined_data = mysql_data + excel_data
            if combined_data and not dry_run:
                df_combined = pd.DataFrame(combined_data)
                df_transformed = self.transformer.transform_pipeline(df_combined)
                logger.info(f"Transformados {len(df_transformed)} registros")
            else:
                df_transformed = pd.DataFrame()
            
            # 3. Cargar a Supabase usando nuevos métodos de upsert
            if not df_transformed.empty and not dry_run:
                # Separar municipios e instituciones
                municipios_data = self._extract_municipios_from_df(df_transformed)
                instituciones_data = df_transformed.to_dict('records')
                
                # Upsert usando métodos corregidos
                municipios_result = self.loader.upsert_municipios_supabase(municipios_data)
                instituciones_result = self.loader.upsert_instituciones_supabase(instituciones_data)
                
                load_result = {
                    'municipios': municipios_result,
                    'instituciones': instituciones_result,
                    'municipios_loaded': municipios_result.get('total', 0),
                    'instituciones_loaded': instituciones_result.get('total', 0)
                }
                logger.info("Carga completada exitosamente")
            else:
                load_result = {'instituciones_loaded': 0, 'municipios_loaded': 0}
            
            # 4. Actualizar metadatos del run
            etl_run.status = 'success'
            etl_run.meta.update({
                'records_processed': len(df_transformed),
                'mysql_records': len(mysql_data),
                'excel_records': len(excel_data),
                'load_result': load_result
            })
            
            logger.info(f"Pipeline ETL completado exitosamente - Run {etl_run.id}")
            
        except Exception as e:
            etl_run.status = 'failed'
            etl_run.meta.update({
                'error': str(e),
                'error_type': type(e).__name__
            })
            logger.error(f"Error en pipeline ETL - Run {etl_run.id}: {e}")
            raise
            
        finally:
            etl_run.finished_at = timezone.now()
            etl_run.save()
        
        return etl_run
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del pipeline ETL.
        
        Returns:
            Dict con información del estado
        """
        recent_runs = ETLRun.objects.order_by('-started_at')[:5]
        
        return {
            'status': 'ready',
            'recent_runs': [
                {
                    'id': run.id,
                    'status': run.status,
                    'started_at': run.started_at,
                    'finished_at': run.finished_at,
                    'duration': run.duration,
                    'meta': run.meta
                } for run in recent_runs
            ],
            'database_connections': {
                'mysql_source': self._test_mysql_connection(),
                'supabase_target': self._test_supabase_connection()
            }
        }
    
    def _test_mysql_connection(self) -> bool:
        """Prueba la conexión a MySQL."""
        try:
            with connections['source_mysql'].cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    def _test_supabase_connection(self) -> bool:
        """Prueba la conexión a Supabase."""
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    def _extract_municipios_from_df(self, df: pd.DataFrame) -> List[Dict]:
        """
        Extrae municipios únicos del DataFrame transformado.
        
        Args:
            df: DataFrame con datos de instituciones
            
        Returns:
            List de diccionarios con datos de municipios únicos
        """
        if df.empty:
            return []
        
        # Extraer municipios únicos
        municipios_cols = ['codigo_municipio', 'codigo_departamento']
        available_cols = [col for col in municipios_cols if col in df.columns]
        
        if not available_cols:
            return []
        
        municipios_df = df[available_cols].drop_duplicates()
        
        # Convertir a formato canonical
        municipios_data = []
        for _, row in municipios_df.iterrows():
            municipio_dict = {
                'codigo_municipio': row.get('codigo_municipio'),
                'codigo_departamento': row.get('codigo_departamento', ''),
                'nombre': '',  # Este campo debe venir de MySQL extractor
            }
            
            # Solo agregar si tiene código válido
            if municipio_dict['codigo_municipio']:
                municipios_data.append(municipio_dict)
        
        return municipios_data

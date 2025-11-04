"""
ETL Service Architecture
========================

Módulos principales:
- extractors: Lectura desde MySQL y Excel
- transformers: Normalización y validación
- loaders: Carga a Supabase
- orchestrator: Coordinación E-T-L
- validators: Validación de calidad
- formatters: Formateo de datos

Flujo:
  Extractor.extract() → DataFrame
  Transformer.transform() → DataFrame normalizado
  Loader.load() → Upsert a Supabase con transacciones
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json

import pandas as pd
from django.db import connection, connections, transaction
from django.conf import settings

logger = logging.getLogger('etl')

# ============================================================================
# Data Classes y Tipos
# ============================================================================

@dataclass
class ExtractionResult:
    """Resultado de la extracción."""
    source: str  # 'mysql' o 'excel'
    table_name: str
    dataframe: pd.DataFrame
    records_count: int
    extraction_time: float
    metadata: Dict[str, Any]


@dataclass
class TransformationResult:
    """Resultado de la transformación."""
    table_name: str
    dataframe: pd.DataFrame
    records_valid: int
    records_invalid: int
    validation_errors: List[Dict[str, Any]]
    transformation_time: float


@dataclass
class LoadingResult:
    """Resultado de la carga."""
    table_name: str
    records_inserted: int
    records_updated: int
    records_failed: int
    loading_time: float
    errors: List[Dict[str, Any]]


# ============================================================================
# Bases abstractas
# ============================================================================

class DataExtractor(ABC):
    """Base para extractores de datos."""
    
    @abstractmethod
    def extract(self, **kwargs) -> ExtractionResult:
        """Extrae datos y retorna un DataFrame."""
        pass


class DataTransformer(ABC):
    """Base para transformadores de datos."""
    
    @abstractmethod
    def transform(self, df: pd.DataFrame, **kwargs) -> TransformationResult:
        """Transforma y valida un DataFrame."""
        pass


class DataLoader(ABC):
    """Base para cargadores de datos."""
    
    @abstractmethod
    def load(self, df: pd.DataFrame, table_name: str, **kwargs) -> LoadingResult:
        """Carga datos a la base de datos destino."""
        pass


# ============================================================================
# Utilidades comunes
# ============================================================================

class HashGenerator:
    """Genera hashes SHA-256 para detectar cambios en filas."""
    
    @staticmethod
    def compute_row_hash(row: pd.Series, exclude_cols: Optional[List[str]] = None) -> str:
        """
        Computa hash SHA-256 de una fila.
        
        Args:
            row: Serie de pandas
            exclude_cols: Columnas a excluir (ej: timestamps, hashes previos)
        
        Returns:
            Hash hexadecimal en minúsculas
        """
        exclude_cols = exclude_cols or ['hash', 'updated_hash', 'created_at', 'updated_at']
        
        # Filtrar columnas
        filtered = row.drop([c for c in exclude_cols if c in row.index])
        
        # Serializar a JSON ordenado (determinístico)
        data_str = json.dumps(filtered.to_dict(), sort_keys=True, default=str)
        
        # Retornar hash SHA-256
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    @staticmethod
    def compute_dataframe_hash(df: pd.DataFrame) -> str:
        """Hash de todo el DataFrame."""
        data_str = pd.util.hash_pandas_object(df, index=True).values.tobytes().hex()
        return hashlib.sha256(data_str.encode()).hexdigest()


class ColumnMapper:
    """Mapea columnas entre fuentes y destino."""
    
    def __init__(self, mapping: Dict[str, str]):
        """
        Args:
            mapping: {columna_fuente: columna_destino}
        """
        self.mapping = mapping
    
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Renombra columnas según el mapeo."""
        # Filtrar solo las columnas que existen
        existing_mapping = {k: v for k, v in self.mapping.items() if k in df.columns}
        return df.rename(columns=existing_mapping)
    
    def get_unmapped_columns(self, df: pd.DataFrame) -> List[str]:
        """Retorna columnas no mapeadas."""
        return [col for col in df.columns if col not in self.mapping]


class TypeConverter:
    """Convierte tipos de datos."""
    
    # Mapeo de tipos comunes
    TYPE_MAP = {
        'integer': 'Int64',  # Nullable
        'float': 'float64',
        'string': 'object',
        'boolean': 'bool',
        'datetime': 'datetime64[ns]',
        'date': 'object',  # Usar object y parsear después
    }
    
    @staticmethod
    def convert_column(series: pd.Series, target_type: str) -> Tuple[pd.Series, Optional[str]]:
        """
        Convierte una columna al tipo especificado.
        
        Returns:
            (serie convertida, mensaje de error o None)
        """
        try:
            dtype = TypeConverter.TYPE_MAP.get(target_type, target_type)
            
            if target_type == 'date':
                # Parsear como fecha y guardar como object
                return pd.to_datetime(series, errors='coerce').dt.date, None
            elif target_type == 'datetime':
                return pd.to_datetime(series, errors='coerce'), None
            else:
                return series.astype(dtype, errors='raise'), None
                
        except Exception as e:
            return series, f"Error convirtiendo {target_type}: {str(e)}"
    
    @staticmethod
    def infer_types(df: pd.DataFrame, type_hints: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """Infiere y aplica tipos de datos."""
        type_hints = type_hints or {}
        
        for col, target_type in type_hints.items():
            if col in df.columns:
                converted, error = TypeConverter.convert_column(df[col], target_type)
                if error:
                    logger.warning(f"Columna {col}: {error}")
                else:
                    df[col] = converted
        
        return df


class ValidationRules:
    """Reglas de validación de datos."""
    
    @staticmethod
    def is_not_null(series: pd.Series, column_name: str) -> Tuple[bool, List[int]]:
        """Valida que no haya nulos."""
        null_indices = series[series.isna()].index.tolist()
        return len(null_indices) == 0, null_indices
    
    @staticmethod
    def is_unique(series: pd.Series, column_name: str) -> Tuple[bool, List[int]]:
        """Valida unicidad."""
        duplicates = series[series.duplicated(keep=False)].index.tolist()
        return len(duplicates) == 0, duplicates
    
    @staticmethod
    def is_in_set(series: pd.Series, allowed_values: set) -> Tuple[bool, List[int]]:
        """Valida que valores estén en conjunto permitido."""
        invalid_indices = series[~series.isin(allowed_values)].index.tolist()
        return len(invalid_indices) == 0, invalid_indices
    
    @staticmethod
    def matches_pattern(series: pd.Series, pattern: str) -> Tuple[bool, List[int]]:
        """Valida contra patrón regex."""
        import re
        invalid_indices = series[~series.astype(str).str.match(pattern)].index.tolist()
        return len(invalid_indices) == 0, invalid_indices
    
    @staticmethod
    def is_in_range(series: pd.Series, min_val: float, max_val: float) -> Tuple[bool, List[int]]:
        """Valida rango de valores numéricos."""
        invalid_indices = series[(series < min_val) | (series > max_val)].index.tolist()
        return len(invalid_indices) == 0, invalid_indices


# ============================================================================
# Logging configurado
# ============================================================================

def setup_etl_logging():
    """Configura loggers para ETL (llamado una vez en settings)."""
    pass  # Ver archivo de configuración LOGGING en settings.py


# ============================================================================
# Exportar submodulos
# ============================================================================

# Loaders
from .loaders import PostgreSQLLoader, SupabaseLoader, LoaderFactory  # noqa: F401, E402

# Orchestrator
from .orchestrator import ETLOrchestrator  # noqa: F401, E402

__all__ = [
    # Data classes
    'ExtractionResult',
    'TransformationResult',
    'LoadingResult',
    # Base classes
    'DataExtractor',
    'DataTransformer',
    'DataLoader',
    # Utilities
    'HashGenerator',
    'ColumnMapper',
    'TypeConverter',
    'ValidationRules',
    # Loaders
    'PostgreSQLLoader',
    'SupabaseLoader',
    'LoaderFactory',
    # Orchestrator
    'ETLOrchestrator',
]


"""
Transformadores de datos: normalización y validación
====================================================

Funciones:
- Mapeo de columnas
- Normalización de valores
- Validación de calidad
- Detección de duplicados
- Hashing para cambios
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import time
import hashlib
import json

import pandas as pd
import numpy as np

from . import (
    DataTransformer, TransformationResult, 
    HashGenerator, ColumnMapper, ValidationRules
)

logger = logging.getLogger('etl.transformation')


class BasicTransformer(DataTransformer):
    """
    Transformador básico con normalización y validación.
    
    Operaciones:
    - Mapeo de columnas
    - Limpieza de espacios
    - Conversión de tipos
    - Normalización de códigos
    - Validación de reglas
    """
    
    def __init__(self,
                 column_mapping: Optional[Dict[str, str]] = None,
                 validation_rules: Optional[Dict[str, Any]] = None,
                 normalize_codes: bool = True):
        """
        Args:
            column_mapping: {columna_origen: columna_destino}
            validation_rules: Reglas de validación por columna
            normalize_codes: Normalizar códigos (mayúsculas, trim)
        """
        self.column_mapping = column_mapping or {}
        self.validation_rules = validation_rules or {}
        self.normalize_codes = normalize_codes
        self.validation_errors = []
    
    def transform(self, df: pd.DataFrame, **kwargs) -> TransformationResult:
        """
        Transforma y valida un DataFrame.
        
        Returns:
            TransformationResult con DF transformado y validaciones
        """
        start_time = time.time()
        table_name = kwargs.get('table_name', 'unknown')
        
        try:
            logger.info(f"Transformando tabla {table_name}...")
            
            # 1. Mapeo de columnas
            if self.column_mapping:
                df = self._map_columns(df)
            
            # 2. Limpieza básica
            df = self._clean_dataframe(df)
            
            # 3. Normalización de códigos
            if self.normalize_codes:
                df = self._normalize_codes(df)
            
            # 4. Validación
            valid_mask, validation_errors = self._validate_rows(df)
            
            # Separar registros válidos e inválidos
            valid_df = df[valid_mask].copy()
            invalid_df = df[~valid_mask].copy()
            
            logger.info(f"Válidos: {len(valid_df)}, Inválidos: {len(invalid_df)}")
            
            # 5. Agregar hashes para cambios
            valid_df = self._add_hashes(valid_df)
            
            transformation_time = time.time() - start_time
            
            result = TransformationResult(
                table_name=table_name,
                dataframe=valid_df,
                records_valid=len(valid_df),
                records_invalid=len(invalid_df),
                validation_errors=validation_errors,
                transformation_time=transformation_time
            )
            
            logger.info(f"✓ Transformación completada en {transformation_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en transformación: {e}")
            raise
    
    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mapea columnas de origen a destino."""
        mapper = ColumnMapper(self.column_mapping)
        df_mapped = mapper.apply(df)
        
        unmapped = mapper.get_unmapped_columns(df)
        if unmapped:
            logger.warning(f"Columnas no mapeadas (se descartan): {unmapped}")
        
        return df_mapped
    
    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Limpieza básica."""
        # Eliminar filas completamente nulas
        df = df.dropna(how='all')
        
        # Trim en strings
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].astype(str).str.strip()
            # Reemplazar strings vacíos con NaN
            df.loc[df[col] == '', col] = np.nan
        
        return df
    
    @staticmethod
    def _normalize_codes(df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza códigos (mayúsculas, sin espacios)."""
        code_columns = [col for col in df.columns if 'codigo' in col.lower() or 'code' in col.lower()]
        
        for col in code_columns:
            if col in df.columns and df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.upper().str.strip()
        
        return df
    
    def _validate_rows(self, df: pd.DataFrame) -> Tuple[pd.Series, List[Dict[str, Any]]]:
        """
        Valida cada fila contra reglas.
        
        Returns:
            (bool mask de filas válidas, lista de errores)
        """
        valid_mask = pd.Series([True] * len(df), index=df.index)
        errors = []
        
        for col, rules in self.validation_rules.items():
            if col not in df.columns:
                logger.warning(f"Columna en reglas pero no en DF: {col}")
                continue
            
            # Regla: obligatoria (not_null)
            if rules.get('required', False):
                is_valid, invalid_indices = ValidationRules.is_not_null(df[col], col)
                if not is_valid:
                    valid_mask.iloc[invalid_indices] = False
                    errors.extend([
                        {'row': idx, 'column': col, 'error': 'Valor obligatorio faltante'}
                        for idx in invalid_indices
                    ])
            
            # Regla: únicos
            if rules.get('unique', False):
                is_valid, invalid_indices = ValidationRules.is_unique(df[col], col)
                if not is_valid:
                    errors.extend([
                        {'row': idx, 'column': col, 'error': 'Valor duplicado (debe ser único)'}
                        for idx in invalid_indices
                    ])
            
            # Regla: en conjunto
            if 'in_set' in rules:
                allowed = set(rules['in_set'])
                is_valid, invalid_indices = ValidationRules.is_in_set(df[col], allowed)
                if not is_valid:
                    valid_mask.iloc[invalid_indices] = False
                    errors.extend([
                        {'row': idx, 'column': col, 'error': f'Valor no permitido (esperados: {allowed})'}
                        for idx in invalid_indices
                    ])
            
            # Regla: patrón regex
            if 'pattern' in rules:
                is_valid, invalid_indices = ValidationRules.matches_pattern(df[col], rules['pattern'])
                if not is_valid:
                    valid_mask.iloc[invalid_indices] = False
                    errors.extend([
                        {'row': idx, 'column': col, 'error': f'No coincide patrón: {rules["pattern"]}'}
                        for idx in invalid_indices
                    ])
            
            # Regla: rango
            if 'min' in rules or 'max' in rules:
                min_val = rules.get('min', float('-inf'))
                max_val = rules.get('max', float('inf'))
                try:
                    is_valid, invalid_indices = ValidationRules.is_in_range(df[col], min_val, max_val)
                    if not is_valid:
                        valid_mask.iloc[invalid_indices] = False
                        errors.extend([
                            {'row': idx, 'column': col, 'error': f'Fuera de rango [{min_val}, {max_val}]'}
                            for idx in invalid_indices
                        ])
                except (TypeError, ValueError):
                    logger.warning(f"No se pudo validar rango en {col} (tipo incompatible)")
        
        return valid_mask, errors
    
    @staticmethod
    def _add_hashes(df: pd.DataFrame) -> pd.DataFrame:
        """Agrega hash SHA-256 para cada fila."""
        df['updated_hash'] = df.apply(
            lambda row: HashGenerator.compute_row_hash(row),
            axis=1
        )
        return df


class InstitutionTransformer(BasicTransformer):
    """
    Transformador especializado para instituciones educativas.
    
    Normalización específica:
    - Códigos DANE, SED, UESValle
    - Municipios válidos
    - Estados conocidos
    - Contacto válido
    """
    
    # Catálogos maestros
    VALID_STATES = {
        'ACTIVO', 'ACTIVA', 'INACTIVO', 'INACTIVA', 
        'SUSPENDIDO', 'EN PROCESO', 'CLAUSURADO'
    }
    
    VALID_SECTORS = {
        'OFICIAL', 'NO OFICIAL', 'PRIVADA', 'PUBLICA'
    }
    
    VALID_ZONES = {
        'URBANA', 'RURAL', 'URBANA-RURAL'
    }
    
    def __init__(self):
        """Inicializa transformador de instituciones."""
        column_mapping = {
            'codigo_dane': 'codigo_dane',
            'nombre_institucion': 'nombre',
            'municipio_codigo': 'codigo_municipio',
            'estado': 'estado',
            'sector': 'sector',
            'zona': 'zona',
        }
        
        validation_rules = {
            'codigo_dane': {'required': True, 'pattern': r'^\d{10,15}$'},
            'nombre': {'required': True},
            'estado': {'required': True, 'in_set': list(self.VALID_STATES)},
            'sector': {'in_set': list(self.VALID_SECTORS)},
            'zona': {'in_set': list(self.VALID_ZONES)},
        }
        
        super().__init__(
            column_mapping=column_mapping,
            validation_rules=validation_rules,
            normalize_codes=True
        )
    
    def transform(self, df: pd.DataFrame, **kwargs) -> TransformationResult:
        """Transforma datos de instituciones."""
        logger.info("Transformando instituciones...")
        
        # Normalizar estado
        df = self._normalize_field(df, 'estado', self.VALID_STATES)
        
        # Normalizar sector
        df = self._normalize_field(df, 'sector', self.VALID_SECTORS)
        
        # Normalizar zona
        df = self._normalize_field(df, 'zona', self.VALID_ZONES)
        
        # Llamar transformación base
        return super().transform(df, **kwargs)
    
    @staticmethod
    def _normalize_field(df: pd.DataFrame, column: str, valid_values: set) -> pd.DataFrame:
        """Normaliza campo contra catálogo."""
        if column not in df.columns:
            return df
        
        # Convertir a mayúsculas y buscar coincidencias
        df[column] = df[column].astype(str).str.upper().str.strip()
        
        # Reemplazar variaciones comunes
        replacements = {
            'ACTIV': 'ACTIVO',
            'INACTIV': 'INACTIVO',
            'OFFICIAL': 'OFICIAL',
            'PUBLIC': 'PUBLICA',
            'PRIVATE': 'PRIVADA',
            'URBA': 'URBANA',
            'RURA': 'RURAL',
        }
        
        for old, new in replacements.items():
            df[column] = df[column].str.replace(old, new, regex=False)
        
        return df


class ChangeDetector:
    """
    Detecta cambios en datos comparando hashes.
    
    Útil para evitar re-procesar registros sin cambios.
    """
    
    @staticmethod
    def detect_changes(new_df: pd.DataFrame,
                      existing_hashes: Dict[str, str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Separa registros nuevos de actualizados.
        
        Args:
            new_df: DataFrame con nuevos datos (debe tener 'unique_key' y 'updated_hash')
            existing_hashes: {unique_key: hash_anterior}
        
        Returns:
            (registros nuevos, registros actualizados)
        """
        if 'updated_hash' not in new_df.columns:
            raise ValueError("DataFrame debe tener columna 'updated_hash'")
        
        new_records = []
        updated_records = []
        
        for _, row in new_df.iterrows():
            key = str(row.get('unique_key', row.name))
            current_hash = row['updated_hash']
            
            if key in existing_hashes:
                # Registro existente
                if existing_hashes[key] != current_hash:
                    # Hash cambió = fila actualizada
                    updated_records.append(row)
                # Si hash igual, ignorar (no hay cambios)
            else:
                # Registro nuevo
                new_records.append(row)
        
        new_df_result = pd.DataFrame(new_records) if new_records else pd.DataFrame()
        upd_df_result = pd.DataFrame(updated_records) if updated_records else pd.DataFrame()
        
        return new_df_result, upd_df_result


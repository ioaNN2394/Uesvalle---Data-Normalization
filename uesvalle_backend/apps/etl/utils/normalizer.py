# etl/utils/normalizer.py
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class Normalizer:
    
    @staticmethod
    def normalize_coordinates(df: pd.DataFrame) -> pd.DataFrame:
        """
        Convierte coordenadas de string a float, RESPETANDO comas decimales.
        """
        for col in ['LONGITUD', 'LATITUD']:
            if col in df.columns:
                try:
                    # Primero convierte a string, luego normaliza
                    df[col] = df[col].astype(str)
                    
                    # Reemplaza coma por punto SOLO para conversión numérica
                    # Evita error: "Can only use .str accessor with string values!"
                    df[col] = df[col].str.replace(',', '.', regex=False)
                    
                    # Convierte a float
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    logger.info(f"Coordenadas normalizadas en {col}")
                except Exception as e:
                    logger.warning(f"Error normalizando {col}: {str(e)}")
        
        return df
    
    @staticmethod
    def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
        """Convierte fechas sin tocar coordinadas."""
        date_cols = ['corte_fecha', 'fecha_nacimiento', 'fecha_visita', 'FECHAVISITA', 'FECHA_VISITA']
        
        for col in date_cols:
            if col in df.columns:
                try:
                    # Asegura que es string antes de convertir a datetime
                    df[col] = df[col].astype(str)
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
                except Exception as e:
                    logger.warning(f"Error normalizando {col}: {str(e)}")
        
        return df
    
    @staticmethod
    def normalize_all_strings(df: pd.DataFrame, exclude_cols: list = None) -> pd.DataFrame:
        """
        Convierte todas las columnas a string primero para evitar errores con .str accessor.
        Útil para transformaciones que vienen de MySQL.
        """
        exclude_cols = exclude_cols or []
        
        for col in df.columns:
            if col not in exclude_cols and df[col].dtype == 'object':
                try:
                    # Si ya tiene None/NaN, respeta esos valores
                    df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) else x)
                except Exception as e:
                    logger.debug(f"No se pudo normalizar {col}: {str(e)}")
        
        return df

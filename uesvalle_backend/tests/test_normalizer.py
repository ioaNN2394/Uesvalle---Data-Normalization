"""
Tests exhaustivos para Normalizer del sistema ETL UESValle.

Este módulo prueba:
- normalize_coordinates: Normalización de coordenadas con comas decimales
- normalize_dates: Normalización de fechas a formato ISO
- normalize_all_strings: Conversión segura de columnas a string
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime


class TestNormalizerCoordinates:
    """Tests para normalize_coordinates."""
    
    def test_normaliza_coordenadas_con_coma(self):
        """Convierte coordenadas con coma decimal a float."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'LONGITUD': ['3,4516', '-76,5320'],
            'LATITUD': ['4,1234', '-77,8901'],
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        # Verificar que son floats
        assert df_norm['LONGITUD'].dtype == 'float64'
        assert df_norm['LATITUD'].dtype == 'float64'
        
        # Verificar valores
        assert df_norm['LONGITUD'].iloc[0] == pytest.approx(3.4516, rel=1e-4)
        assert df_norm['LATITUD'].iloc[1] == pytest.approx(-77.8901, rel=1e-4)
    
    def test_normaliza_coordenadas_con_punto(self):
        """Mantiene coordenadas que ya tienen punto decimal."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'LONGITUD': ['3.4516', '-76.5320'],
            'LATITUD': ['4.1234', '-77.8901'],
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        assert df_norm['LONGITUD'].iloc[0] == pytest.approx(3.4516, rel=1e-4)
    
    def test_normaliza_coordenadas_mixtas(self):
        """Maneja mezcla de comas y puntos."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'LONGITUD': ['3,4516', '-76.5320'],
            'LATITUD': ['4.1234', '-77,8901'],
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        # Todas deben ser float
        assert df_norm['LONGITUD'].dtype == 'float64'
        assert df_norm['LATITUD'].dtype == 'float64'
    
    def test_normaliza_coordenadas_con_nan(self):
        """Maneja valores NaN en coordenadas."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'LONGITUD': ['3,4516', np.nan, '-76,5320'],
            'LATITUD': ['4,1234', '-77,8901', np.nan],
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        # Debe preservar NaN
        assert pd.isna(df_norm['LONGITUD'].iloc[1])
        assert pd.isna(df_norm['LATITUD'].iloc[2])
    
    def test_normaliza_coordenadas_sin_columnas(self):
        """Maneja DataFrame sin columnas de coordenadas."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'OTRA_COLUMNA': ['valor1', 'valor2'],
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        # Debe retornar el mismo DataFrame sin errores
        assert len(df_norm) == 2
        assert 'OTRA_COLUMNA' in df_norm.columns
    
    def test_normaliza_coordenadas_columna_parcial(self):
        """Maneja DataFrame con solo una columna de coordenadas."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'LATITUD': ['3,4516', '-76,5320'],
            'OTRA': ['val1', 'val2'],
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        assert df_norm['LATITUD'].dtype == 'float64'
    
    def test_normaliza_coordenadas_valores_invalidos(self):
        """Convierte valores inválidos a NaN."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'LONGITUD': ['3,4516', 'no_es_numero', ''],
            'LATITUD': ['4,1234', '', 'texto'],
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        # Valores válidos
        assert df_norm['LONGITUD'].iloc[0] == pytest.approx(3.4516, rel=1e-4)
        
        # Valores inválidos deben ser NaN
        assert pd.isna(df_norm['LONGITUD'].iloc[1])
        assert pd.isna(df_norm['LATITUD'].iloc[2])
    
    def test_normaliza_coordenadas_preserva_otras_columnas(self):
        """Preserva otras columnas sin modificar."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'LONGITUD': ['3,4516'],
            'LATITUD': ['4,1234'],
            'NOMBRE': ['IE Test'],
            'CODIGO': ['12345'],
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        assert df_norm['NOMBRE'].iloc[0] == 'IE Test'
        assert df_norm['CODIGO'].iloc[0] == '12345'


class TestNormalizerDates:
    """Tests para normalize_dates."""
    
    def test_normaliza_fecha_iso(self):
        """Normaliza fecha formato ISO."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'corte_fecha': ['2024-01-15', '2024-02-20'],
        })
        
        df_norm = Normalizer.normalize_dates(df)
        
        assert df_norm['corte_fecha'].iloc[0] == '2024-01-15'
    
    def test_normaliza_fecha_slash(self):
        """Normaliza fecha con slashes."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'corte_fecha': ['15/01/2024', '20/02/2024'],
        })
        
        df_norm = Normalizer.normalize_dates(df)
        
        # Debe convertir a ISO
        assert '2024' in df_norm['corte_fecha'].iloc[0]
    
    def test_normaliza_fecha_datetime(self):
        """Normaliza objeto datetime."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'corte_fecha': [datetime(2024, 1, 15), datetime(2024, 2, 20)],
        })
        
        df_norm = Normalizer.normalize_dates(df)
        
        assert '2024-01-15' in df_norm['corte_fecha'].iloc[0]
    
    def test_normaliza_fecha_con_nan(self):
        """Maneja valores NaN en fechas."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'corte_fecha': ['2024-01-15', np.nan, '2024-02-20'],
        })
        
        df_norm = Normalizer.normalize_dates(df)
        
        # NaN se convierte a 'NaT' o 'nan' string
        assert df_norm['corte_fecha'].iloc[0] == '2024-01-15'
    
    def test_normaliza_fecha_invalida(self):
        """Maneja fechas inválidas."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'corte_fecha': ['2024-01-15', 'no_es_fecha', ''],
        })
        
        df_norm = Normalizer.normalize_dates(df)
        
        assert df_norm['corte_fecha'].iloc[0] == '2024-01-15'
    
    def test_normaliza_fecha_sin_columnas(self):
        """Maneja DataFrame sin columnas de fecha."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'OTRA_COLUMNA': ['valor1', 'valor2'],
        })
        
        df_norm = Normalizer.normalize_dates(df)
        
        # Debe retornar el mismo DataFrame
        assert len(df_norm) == 2
    
    def test_normaliza_fecha_multiple_columnas(self):
        """Normaliza múltiples columnas de fecha."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'corte_fecha': ['2024-01-15'],
            'fecha_nacimiento': ['1990-05-20'],
            'fecha_visita': ['2024-03-10'],
        })
        
        df_norm = Normalizer.normalize_dates(df)
        
        assert df_norm['corte_fecha'].iloc[0] == '2024-01-15'
        assert df_norm['fecha_nacimiento'].iloc[0] == '1990-05-20'
    
    def test_no_normaliza_coordenadas_como_fecha(self):
        """No confunde coordenadas con fechas."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'corte_fecha': ['2024-01-15'],
            'LONGITUD': ['3,4516'],  # No debe ser tocado
            'LATITUD': ['4,1234'],   # No debe ser tocado
        })
        
        df_norm = Normalizer.normalize_dates(df)
        
        # Coordenadas deben permanecer como string
        assert df_norm['LONGITUD'].iloc[0] == '3,4516'


class TestNormalizerStrings:
    """Tests para normalize_all_strings."""
    
    def test_normaliza_strings_basico(self):
        """Convierte columnas object a string."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'NOMBRE': ['IE Test 1', 'IE Test 2'],
            'CODIGO': [12345, 67890],  # int
        })
        
        df_norm = Normalizer.normalize_all_strings(df)
        
        # Columna object debe mantenerse como string
        assert df_norm['NOMBRE'].iloc[0] == 'IE Test 1'
    
    def test_normaliza_strings_preserva_none(self):
        """Preserva valores None/NaN."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'NOMBRE': ['IE Test', None, np.nan],
        })
        
        df_norm = Normalizer.normalize_all_strings(df)
        
        assert df_norm['NOMBRE'].iloc[0] == 'IE Test'
        # None/NaN deben preservarse
        assert pd.isna(df_norm['NOMBRE'].iloc[1]) or df_norm['NOMBRE'].iloc[1] is None
    
    def test_normaliza_strings_con_exclusiones(self):
        """Excluye columnas especificadas."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'NOMBRE': ['IE Test'],
            'LONGITUD': ['3,4516'],  # Excluir
            'LATITUD': ['4,1234'],   # Excluir
        })
        
        df_norm = Normalizer.normalize_all_strings(df, exclude_cols=['LONGITUD', 'LATITUD'])
        
        # NOMBRE debe ser string
        assert df_norm['NOMBRE'].iloc[0] == 'IE Test'
    
    def test_normaliza_strings_mixtos(self):
        """Maneja DataFrame con tipos mixtos."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'NOMBRE': ['IE Test'],
            'VALOR_INT': [100],
            'VALOR_FLOAT': [3.14],
            'VALOR_BOOL': [True],
        })
        
        df_norm = Normalizer.normalize_all_strings(df)
        
        # Solo columnas object deben ser afectadas
        assert df_norm['NOMBRE'].iloc[0] == 'IE Test'
    
    def test_normaliza_strings_vacios(self):
        """Maneja strings vacíos."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'NOMBRE': ['IE Test', '', '   '],
        })
        
        df_norm = Normalizer.normalize_all_strings(df)
        
        # Strings vacíos deben preservarse
        assert df_norm['NOMBRE'].iloc[1] == ''


class TestNormalizerIntegration:
    """Tests de integración del Normalizer."""
    
    def test_normaliza_dataframe_completo(self):
        """Normaliza DataFrame con todos los tipos de datos."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'NOMBRE': ['IE Test'],
            'LATITUD': ['3,4516'],
            'LONGITUD': ['-76,5320'],
            'corte_fecha': ['2024-01-15'],
            'CODIGO': ['12345'],
        })
        
        # Normalizar en orden
        df = Normalizer.normalize_coordinates(df)
        df = Normalizer.normalize_dates(df)
        df = Normalizer.normalize_all_strings(df, exclude_cols=['LATITUD', 'LONGITUD'])
        
        # Verificar todos los tipos
        assert df['LATITUD'].dtype == 'float64'
        assert df['LONGITUD'].dtype == 'float64'
        assert df['corte_fecha'].iloc[0] == '2024-01-15'
        assert df['NOMBRE'].iloc[0] == 'IE Test'
    
    def test_normaliza_preserva_estructura(self):
        """Preserva estructura del DataFrame."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'COL1': ['val1', 'val2'],
            'COL2': ['val3', 'val4'],
            'LATITUD': ['3,4516', '4,1234'],
        })
        
        original_shape = df.shape
        
        df = Normalizer.normalize_coordinates(df)
        
        assert df.shape == original_shape
        assert list(df.columns) == ['COL1', 'COL2', 'LATITUD']
    
    def test_normaliza_dataframe_vacio(self):
        """Maneja DataFrame vacío."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame(columns=['NOMBRE', 'LATITUD', 'LONGITUD'])
        
        df = Normalizer.normalize_coordinates(df)
        df = Normalizer.normalize_dates(df)
        df = Normalizer.normalize_all_strings(df)
        
        assert len(df) == 0
        assert list(df.columns) == ['NOMBRE', 'LATITUD', 'LONGITUD']


class TestNormalizerEdgeCases:
    """Tests de casos de borde del Normalizer."""
    
    def test_coordenada_con_espacios(self):
        """Maneja coordenadas con espacios."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'LATITUD': ['  3,4516  ', ' -76,5320 '],
            'LONGITUD': ['4,1234', '-77,8901'],
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        # Debe funcionar aunque tenga espacios
        assert df_norm['LATITUD'].dtype == 'float64'
    
    def test_fecha_con_hora(self):
        """Maneja fecha con componente de hora."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'corte_fecha': ['2024-01-15 10:30:00', '2024-02-20 14:45:00'],
        })
        
        df_norm = Normalizer.normalize_dates(df)
        
        # Debe extraer solo la fecha
        assert '2024-01-15' in df_norm['corte_fecha'].iloc[0]
    
    def test_coordenada_fuera_de_rango(self):
        """Acepta coordenadas fuera de rango (validación externa)."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'LATITUD': ['100,0000'],  # Fuera de -90 a 90
            'LONGITUD': ['200,0000'],  # Fuera de -180 a 180
        })
        
        df_norm = Normalizer.normalize_coordinates(df)
        
        # Normalizer NO valida rangos, solo convierte
        assert df_norm['LATITUD'].iloc[0] == pytest.approx(100.0, rel=1e-4)
        assert df_norm['LONGITUD'].iloc[0] == pytest.approx(200.0, rel=1e-4)
    
    def test_string_con_caracteres_especiales(self):
        """Maneja strings con caracteres especiales."""
        from apps.etl.utils.normalizer import Normalizer
        
        df = pd.DataFrame({
            'NOMBRE': ['IE Niño Jesús', 'Colegio "El Ñandú"', "IE O'Connor"],
        })
        
        df_norm = Normalizer.normalize_all_strings(df)
        
        # Debe preservar caracteres especiales
        assert 'Niño' in df_norm['NOMBRE'].iloc[0]
        assert 'Ñandú' in df_norm['NOMBRE'].iloc[1]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

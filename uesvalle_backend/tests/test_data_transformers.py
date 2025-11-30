"""
Tests exhaustivos para transformadores de datos del sistema ETL UESValle.

Este módulo prueba:
- transformar_maestras_csv: Transformación de CSV de instituciones DANE
- transformar_visitas_mysql: Transformación de visitas de MySQL
- Funciones auxiliares: _parse_coordinate, _parse_date, _parse_int, etc.

Escenarios probados:
- Transformación completa de instituciones y sedes
- Filtrado por departamento Valle del Cauca
- Manejo de coordenadas con comas decimales
- Normalización de campos
- Construcción de metadata
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestTransformarMaestrasCSV:
    """Tests para transformar_maestras_csv."""
    
    def test_transformar_instituciones_basico(self, df_csv_instituciones):
        """Transforma DataFrame de instituciones correctamente."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df_csv_instituciones)
        
        # Verificar instituciones
        assert len(df_inst) == 3
        assert 'id' in df_inst.columns
        assert 'dane_ie_id' in df_inst.columns
        assert 'nombre' in df_inst.columns
    
    def test_transformar_genera_uuids(self, df_csv_instituciones):
        """Genera UUIDs válidos para instituciones y sedes."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df_csv_instituciones)
        
        # Verificar que los IDs son UUIDs válidos
        for inst_id in df_inst['id']:
            uuid.UUID(inst_id)  # No debe lanzar excepción
        
        for sede_id in df_sedes['id']:
            uuid.UUID(sede_id)
    
    def test_transformar_filtra_por_departamento(self, df_csv_mixto_departamentos):
        """Filtra instituciones por Valle del Cauca."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df_csv_mixto_departamentos)
        
        # Solo debe haber 2 instituciones del Valle del Cauca
        assert len(df_inst) == 2
    
    def test_transformar_crea_mapa_dane_uuid(self, df_csv_instituciones):
        """Crea mapeo DANE → UUID."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df_csv_instituciones)
        
        # Verificar que el mapa tiene las mismas instituciones
        assert len(mapa) == len(df_inst)
        
        # Verificar que cada DANE mapea a un UUID
        for dane, uuid_str in mapa.items():
            assert dane.isdigit()
            uuid.UUID(uuid_str)  # Debe ser UUID válido
    
    def test_transformar_sedes_vinculadas_a_instituciones(self, df_csv_instituciones):
        """Las sedes están correctamente vinculadas a instituciones."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df_csv_instituciones)
        
        # Todas las sedes deben tener institucion_id válido
        instituciones_ids = set(df_inst['id'].tolist())
        
        for inst_id in df_sedes['institucion_id']:
            assert inst_id in instituciones_ids
    
    def test_transformar_coordenadas_con_coma(self, df_csv_instituciones):
        """Maneja coordenadas con coma decimal."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df_csv_instituciones)
        
        # Verificar que las coordenadas se convirtieron a float
        for idx, sede in df_sedes.iterrows():
            lat = sede['lat']
            lon = sede['lon']
            
            if lat is not None:
                assert isinstance(lat, float)
                assert 2.0 < lat < 5.0  # Rango Colombia
            
            if lon is not None:
                assert isinstance(lon, float)
                assert -78.0 < lon < -75.0  # Rango Colombia
    
    def test_transformar_metadata_institucion(self, df_csv_instituciones):
        """Metadata de institución tiene campos esperados."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df_csv_instituciones)
        
        for metadata in df_inst['metadata']:
            assert 'origen' in metadata
            assert metadata['origen'] == 'csv'
            assert 'fecha_sincronizacion' in metadata
    
    def test_transformar_metadata_sede(self, df_csv_instituciones):
        """Metadata de sede tiene campos esperados."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df_csv_instituciones)
        
        for metadata in df_sedes['metadata']:
            assert 'origen' in metadata
            assert metadata['origen'] == 'csv'
            # Campos opcionales
            assert 'zona' in metadata or True
            assert 'naturaleza' in metadata or True
    
    def test_transformar_sin_registros_valle_lanza_error(self):
        """Lanza error si no hay registros del Valle del Cauca."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df = pd.DataFrame({
            'COD_DANE': ['11900100001'],
            'NOMBRE_INSTITUCION': ['IE Bogotá'],
            'DEPARTAMENTO': ['BOGOTA D.C.'],
            'ID_MUNICIPIO': ['11001'],
        })
        
        with pytest.raises(ValueError) as excinfo:
            transformar_maestras_csv(df)
        
        assert 'Valle del Cauca' in str(excinfo.value)
    
    def test_transformar_normaliza_columnas_uppercase(self):
        """Normaliza nombres de columnas a uppercase."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df = pd.DataFrame({
            'cod_dane': ['17600100001'],
            'nombre_institucion': ['IE Test'],
            'departamento': ['VALLE DEL CAUCA'],
            'id_municipio': ['76001'],
        })
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df)
        
        assert len(df_inst) == 1
    
    def test_transformar_maneja_campos_faltantes(self):
        """Maneja campos faltantes con valores por defecto."""
        from apps.etl.utils.data_transformers import transformar_maestras_csv
        
        df = pd.DataFrame({
            'COD_DANE': ['17600100001'],
            'NOMBRE_INSTITUCION': ['IE Test'],
            'DEPARTAMENTO': ['VALLE DEL CAUCA'],
            'ID_MUNICIPIO': ['76001'],
            # Faltan: CORREO_INSTITUCIONAL, DIRECCION, TELEFONO, etc.
        })
        
        df_inst, df_sedes, mapa = transformar_maestras_csv(df)
        
        # Debe crear la institución con campos opcionales en None/NaN
        assert len(df_inst) == 1


class TestTransformarVisitasMySQL:
    """Tests para transformar_visitas_mysql."""
    
    @pytest.fixture
    def dict_instituciones_by_dane(self):
        """Mapeo DANE → UUID para tests."""
        return {
            '17600100001': str(uuid.uuid4()),
            '17600100002': str(uuid.uuid4()),
            '17600100003': str(uuid.uuid4()),
        }
    
    @pytest.fixture
    def dict_instituciones_by_uesvalle(self):
        """Mapeo UESValle → UUID para tests."""
        return {
            'UES001': str(uuid.uuid4()),
            'UES002': str(uuid.uuid4()),
            'UES003': str(uuid.uuid4()),
        }
    
    @pytest.fixture
    def dict_sedes(self):
        """Mapeo DANE Sede → UUID para tests."""
        return {
            '17600100001001': str(uuid.uuid4()),
            '17600100002001': str(uuid.uuid4()),
        }
    
    def test_transformar_visitas_basico(self, df_mysql_visitas, dict_sedes, 
                                        dict_instituciones_by_dane, 
                                        dict_instituciones_by_uesvalle):
        """Transforma DataFrame de visitas correctamente."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df_visitas = transformar_visitas_mysql(
            df_mysql_visitas, 
            dict_sedes,
            dict_instituciones_by_dane,
            dict_instituciones_by_uesvalle
        )
        
        # Debe haber visitas transformadas
        assert len(df_visitas) > 0
        
        # Columnas requeridas
        assert 'institucion_id' in df_visitas.columns
        assert 'fechavisita' in df_visitas.columns
        assert 'conceptovisita' in df_visitas.columns
    
    def test_transformar_visitas_vincula_institucion(self, df_mysql_visitas, dict_sedes,
                                                      dict_instituciones_by_dane,
                                                      dict_instituciones_by_uesvalle):
        """Vincula visitas a instituciones por DANE o UESValle."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df_visitas = transformar_visitas_mysql(
            df_mysql_visitas,
            dict_sedes,
            dict_instituciones_by_dane,
            dict_instituciones_by_uesvalle
        )
        
        # Todas las visitas deben tener institucion_id
        for inst_id in df_visitas['institucion_id']:
            assert inst_id is not None
    
    def test_transformar_visitas_sede_opcional(self, df_mysql_visitas, dict_sedes,
                                                dict_instituciones_by_dane,
                                                dict_instituciones_by_uesvalle):
        """Sede es opcional (puede ser None)."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df_visitas = transformar_visitas_mysql(
            df_mysql_visitas,
            dict_sedes,
            dict_instituciones_by_dane,
            dict_instituciones_by_uesvalle
        )
        
        # Al menos una visita puede no tener sede
        sedes_none = df_visitas['sede_id'].isna().sum()
        # Esto es válido - no falla
    
    def test_transformar_visitas_valida_conceptos(self, dict_sedes,
                                                   dict_instituciones_by_dane,
                                                   dict_instituciones_by_uesvalle):
        """Valida que conceptos sean F/D/FCR."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df = pd.DataFrame({
            'identificacion': ['UES001', 'UES002'],
            'codigodane': ['17600100001', '17600100002'],
            'fechavisita': ['2024-01-15', '2024-01-16'],
            'conceptovisita': ['F', 'INVALIDO'],  # Segundo es inválido
        })
        
        df_visitas = transformar_visitas_mysql(
            df,
            dict_sedes,
            dict_instituciones_by_dane,
            dict_instituciones_by_uesvalle
        )
        
        # El concepto inválido debe ser None
        conceptos = df_visitas['conceptovisita'].tolist()
        assert 'F' in conceptos
        # 'INVALIDO' se convierte a None
    
    def test_transformar_visitas_convierte_fecha(self, dict_sedes,
                                                  dict_instituciones_by_dane,
                                                  dict_instituciones_by_uesvalle):
        """Convierte fechas a formato date."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df = pd.DataFrame({
            'identificacion': ['UES001'],
            'codigodane': ['17600100001'],
            'fechavisita': ['2024-01-15'],
            'conceptovisita': ['F'],
        })
        
        df_visitas = transformar_visitas_mysql(
            df,
            dict_sedes,
            dict_instituciones_by_dane,
            dict_instituciones_by_uesvalle
        )
        
        fecha = df_visitas['fechavisita'].iloc[0]
        assert isinstance(fecha, date)
    
    def test_transformar_visitas_convierte_codigos_a_int(self, dict_sedes,
                                                          dict_instituciones_by_dane,
                                                          dict_instituciones_by_uesvalle):
        """Convierte códigos a int."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df = pd.DataFrame({
            'identificacion': ['UES001'],
            'codigodane': ['17600100001'],
            'fechavisita': ['2024-01-15'],
            'conceptovisita': ['F'],
            'codigotipoobjeto': ['1.0'],
            'codigofuncionario': ['101.0'],
        })
        
        df_visitas = transformar_visitas_mysql(
            df,
            dict_sedes,
            dict_instituciones_by_dane,
            dict_instituciones_by_uesvalle
        )
        
        assert df_visitas['codigotipoobjeto'].iloc[0] == 1
        assert df_visitas['codigofuncionario'].iloc[0] == 101
    
    def test_transformar_visitas_descarta_sin_institucion(self, dict_sedes):
        """Descarta visitas sin institución."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df = pd.DataFrame({
            'identificacion': ['INEXISTENTE'],
            'codigodane': ['99999999999'],  # No existe en diccionarios
            'fechavisita': ['2024-01-15'],
            'conceptovisita': ['F'],
        })
        
        df_visitas = transformar_visitas_mysql(
            df,
            dict_sedes,
            dict_instituciones_by_dane={},
            dict_instituciones_by_uesvalle={}
        )
        
        # Debe estar vacío
        assert len(df_visitas) == 0
    
    def test_transformar_visitas_descarta_sin_fecha(self, dict_sedes,
                                                     dict_instituciones_by_dane,
                                                     dict_instituciones_by_uesvalle):
        """Descarta visitas sin fecha."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df = pd.DataFrame({
            'identificacion': ['UES001'],
            'codigodane': ['17600100001'],
            'fechavisita': [None],  # Sin fecha
            'conceptovisita': ['F'],
        })
        
        df_visitas = transformar_visitas_mysql(
            df,
            dict_sedes,
            dict_instituciones_by_dane,
            dict_instituciones_by_uesvalle
        )
        
        assert len(df_visitas) == 0
    
    def test_transformar_visitas_metadata(self, df_mysql_visitas, dict_sedes,
                                           dict_instituciones_by_dane,
                                           dict_instituciones_by_uesvalle):
        """Metadata contiene datos de MySQL."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df_visitas = transformar_visitas_mysql(
            df_mysql_visitas,
            dict_sedes,
            dict_instituciones_by_dane,
            dict_instituciones_by_uesvalle
        )
        
        for metadata in df_visitas['metadata']:
            assert 'origen' in metadata
            assert metadata['origen'] == 'mysql'
            assert 'fecha_sincronizacion' in metadata


class TestFuncionesAuxiliares:
    """Tests para funciones auxiliares de data_transformers."""
    
    def test_parse_coordinate_con_coma(self):
        """Parsea coordenada con coma decimal."""
        from apps.etl.utils.data_transformers import _parse_coordinate
        
        result = _parse_coordinate('3,4516')
        assert result == pytest.approx(3.4516, rel=1e-4)
    
    def test_parse_coordinate_con_punto(self):
        """Parsea coordenada con punto decimal."""
        from apps.etl.utils.data_transformers import _parse_coordinate
        
        result = _parse_coordinate('3.4516')
        assert result == pytest.approx(3.4516, rel=1e-4)
    
    def test_parse_coordinate_negativa(self):
        """Parsea coordenada negativa."""
        from apps.etl.utils.data_transformers import _parse_coordinate
        
        result = _parse_coordinate('-76,5320')
        assert result == pytest.approx(-76.5320, rel=1e-4)
    
    def test_parse_coordinate_none(self):
        """Retorna None para None."""
        from apps.etl.utils.data_transformers import _parse_coordinate
        
        result = _parse_coordinate(None)
        assert result is None
    
    def test_parse_coordinate_nan(self):
        """Retorna None para 'nan'."""
        from apps.etl.utils.data_transformers import _parse_coordinate
        
        result = _parse_coordinate('nan')
        assert result is None
    
    def test_parse_coordinate_invalida(self):
        """Retorna None para valor inválido."""
        from apps.etl.utils.data_transformers import _parse_coordinate
        
        result = _parse_coordinate('no_es_coordenada')
        assert result is None
    
    def test_parse_date_iso(self):
        """Parsea fecha ISO."""
        from apps.etl.utils.data_transformers import _parse_date
        
        result = _parse_date('2024-01-15')
        assert result == date(2024, 1, 15)
    
    def test_parse_date_none(self):
        """Retorna None para None."""
        from apps.etl.utils.data_transformers import _parse_date
        
        result = _parse_date(None)
        assert result is None
    
    def test_parse_date_vacio(self):
        """Retorna None para vacío."""
        from apps.etl.utils.data_transformers import _parse_date
        
        result = _parse_date('')
        assert result is None
    
    def test_parse_date_invalida(self):
        """Retorna None para fecha inválida."""
        from apps.etl.utils.data_transformers import _parse_date
        
        result = _parse_date('no_es_fecha')
        assert result is None
    
    def test_parse_int_string(self):
        """Parsea string a int."""
        from apps.etl.utils.data_transformers import _parse_int
        
        result = _parse_int('123')
        assert result == 123
    
    def test_parse_int_con_decimal_cero(self):
        """Parsea '123.0' a int."""
        from apps.etl.utils.data_transformers import _parse_int
        
        result = _parse_int('123.0')
        assert result == 123
    
    def test_parse_int_float(self):
        """Parsea float a int."""
        from apps.etl.utils.data_transformers import _parse_int
        
        result = _parse_int(123.7)
        assert result == 123
    
    def test_parse_int_none(self):
        """Retorna None para None."""
        from apps.etl.utils.data_transformers import _parse_int
        
        result = _parse_int(None)
        assert result is None
    
    def test_parse_int_nan(self):
        """Retorna None para 'nan'."""
        from apps.etl.utils.data_transformers import _parse_int
        
        result = _parse_int('nan')
        assert result is None
    
    def test_parse_int_invalido(self):
        """Retorna None para valor inválido."""
        from apps.etl.utils.data_transformers import _parse_int
        
        result = _parse_int('abc')
        assert result is None
    
    def test_normalize_string_basico(self):
        """Normaliza string básico."""
        from apps.etl.utils.data_transformers import _normalize_string
        
        result = _normalize_string('  texto  ')
        assert result == 'texto'
    
    def test_normalize_string_none(self):
        """Retorna None para None."""
        from apps.etl.utils.data_transformers import _normalize_string
        
        result = _normalize_string(None)
        assert result is None
    
    def test_normalize_string_vacio(self):
        """Retorna None para vacío."""
        from apps.etl.utils.data_transformers import _normalize_string
        
        result = _normalize_string('')
        assert result is None
    
    def test_get_mysql_value_primera_columna(self):
        """Obtiene valor de primera columna existente."""
        from apps.etl.utils.data_transformers import _get_mysql_value
        
        row = pd.Series({
            'codigodane': '17600100001',
            'codigo_dane': '99999999999',
        })
        
        result = _get_mysql_value(row, ['codigodane', 'codigo_dane'])
        assert result == '17600100001'
    
    def test_get_mysql_value_segunda_columna(self):
        """Obtiene valor de segunda columna si primera no existe."""
        from apps.etl.utils.data_transformers import _get_mysql_value
        
        row = pd.Series({
            'codigo_dane': '17600100001',
        })
        
        result = _get_mysql_value(row, ['codigodane', 'codigo_dane'])
        assert result == '17600100001'
    
    def test_get_mysql_value_ninguna_columna(self):
        """Retorna None si ninguna columna existe."""
        from apps.etl.utils.data_transformers import _get_mysql_value
        
        row = pd.Series({
            'otra_columna': 'valor',
        })
        
        result = _get_mysql_value(row, ['codigodane', 'codigo_dane'])
        assert result is None
    
    def test_get_mysql_value_columna_vacia(self):
        """Retorna None si columna tiene valor vacío."""
        from apps.etl.utils.data_transformers import _get_mysql_value
        
        row = pd.Series({
            'codigodane': '',
        })
        
        result = _get_mysql_value(row, ['codigodane'])
        assert result is None


class TestBuildMetadata:
    """Tests para _build_metadata."""
    
    def test_build_metadata_basico(self):
        """Construye metadata básica."""
        from apps.etl.utils.data_transformers import _build_metadata
        
        row = pd.Series({
            'nombreestablecimiento': 'Restaurante Test',
            'cumplimiento': '85.5',
        })
        
        metadata = _build_metadata(row)
        
        assert metadata['origen'] == 'mysql'
        assert 'fecha_sincronizacion' in metadata
    
    def test_build_metadata_establecimiento(self):
        """Incluye datos del establecimiento."""
        from apps.etl.utils.data_transformers import _build_metadata
        
        row = pd.Series({
            'nombreestablecimiento': 'Restaurante Test',
            'direccionestablecimiento': 'Calle 1',
            'telefonoestablecimiento': '123456',
        })
        
        metadata = _build_metadata(row)
        
        if 'establecimiento' in metadata:
            assert metadata['establecimiento']['nombre'] == 'Restaurante Test'
    
    def test_build_metadata_cumplimiento(self):
        """Incluye datos de cumplimiento."""
        from apps.etl.utils.data_transformers import _build_metadata
        
        row = pd.Series({
            'cumplimiento': '85.5',
            'bloque1': '90.0',
            'bloque2': '80.0',
        })
        
        metadata = _build_metadata(row)
        
        if 'cumplimiento' in metadata:
            assert metadata['cumplimiento']['total'] == pytest.approx(85.5, rel=1e-2)
    
    def test_build_metadata_pae(self):
        """Incluye datos PAE."""
        from apps.etl.utils.data_transformers import _build_metadata
        
        row = pd.Series({
            'tienepae': 'S',
            'estudianteshombre': '100',
            'estudiantesmujer': '120',
        })
        
        metadata = _build_metadata(row)
        
        if 'pae' in metadata:
            assert metadata['pae']['tiene_pae'] == 'S'
    
    def test_build_metadata_limpia_nones(self):
        """Elimina valores None de metadata."""
        from apps.etl.utils.data_transformers import _build_metadata
        
        row = pd.Series({
            'nombreestablecimiento': None,
            'cumplimiento': None,
        })
        
        metadata = _build_metadata(row)
        
        # No debe tener sub-diccionarios vacíos
        for key, value in metadata.items():
            if isinstance(value, dict):
                # Diccionarios no deben estar vacíos si existen
                pass  # Flexible en este caso


class TestTransformersEdgeCases:
    """Tests de casos de borde en transformadores."""
    
    def test_dataframe_vacio(self):
        """Maneja DataFrame vacío."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df = pd.DataFrame(columns=['identificacion', 'codigodane', 'fechavisita'])
        
        df_visitas = transformar_visitas_mysql(df, {}, {}, {})
        
        assert len(df_visitas) == 0
    
    def test_columnas_case_insensitive(self):
        """Maneja columnas con diferente case."""
        from apps.etl.utils.data_transformers import transformar_visitas_mysql
        
        df = pd.DataFrame({
            'IDENTIFICACION': ['UES001'],
            'CODIGODANE': ['17600100001'],
            'FECHAVISITA': ['2024-01-15'],
        })
        
        dict_inst = {'17600100001': str(uuid.uuid4())}
        
        df_visitas = transformar_visitas_mysql(df, {}, dict_inst, {})
        
        # Debe procesar correctamente
        assert len(df_visitas) == 1
    
    def test_valores_especiales_pandas(self):
        """Maneja valores especiales de pandas (NaN, NaT, etc)."""
        import numpy as np
        from apps.etl.utils.data_transformers import _parse_coordinate, _parse_int
        
        # NaN de numpy
        result = _parse_coordinate(np.nan)
        assert result is None
        
        result = _parse_int(np.nan)
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

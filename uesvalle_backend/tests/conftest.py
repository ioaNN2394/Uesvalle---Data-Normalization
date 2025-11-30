"""
Configuración global de pytest y fixtures compartidos para tests del proyecto UESValle.

Este archivo contiene:
- Configuración de Django para tests
- Fixtures de modelos (Institucion, Sede, Visita, etc.)
- Fixtures de datos de prueba (DataFrames, CSVs mockeados)
- Utilities para tests
"""
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import pandas as pd

# Configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')

import django
django.setup()

from django.test import TestCase
from django.utils import timezone

# Importaciones de modelos
from apps.etl.models import (
    ETLRun, ETLFile, Institucion, Sede, Visita, 
    DimMunicipio, Notification, FactMatricula, 
    FactMatriculaEtnica, PaeAsignacion
)


# =============================================================================
# FIXTURES DE CONFIGURACIÓN
# =============================================================================

@pytest.fixture
def django_db_setup():
    """Setup para tests que requieren base de datos."""
    pass


@pytest.fixture
def settings_override():
    """Permite sobrescribir settings de Django en tests."""
    from django.conf import settings
    original_debug = settings.DEBUG
    yield settings
    settings.DEBUG = original_debug


# =============================================================================
# FIXTURES DE MODELOS - INSTITUCIONES
# =============================================================================

@pytest.fixture
def institucion_data():
    """Datos base para crear una institución."""
    return {
        'id': uuid.uuid4(),
        'nombre': 'Institución Educativa Test',
        'dane_ie_id': '17600100001',
        'uesvalle_ie_id': 'UES001',
        'codigo_municipio': '76001',
        'direccion': 'Calle 1 #2-3',
        'telefono': '123456789',
        'email': 'test@institucion.edu.co',
        'estado': 'ACTIVA',
        'lat': Decimal('3.4516'),
        'lon': Decimal('-76.5320'),
        'metadata': {
            'origen': 'test',
            'fecha_sincronizacion': datetime.now().isoformat()
        }
    }


@pytest.fixture
def institucion_factory():
    """Factory para crear instituciones con datos personalizados."""
    def _create_institucion(**kwargs):
        defaults = {
            'id': uuid.uuid4(),
            'nombre': f'Institución Test {uuid.uuid4().hex[:6]}',
            'dane_ie_id': f'1760010{str(uuid.uuid4().int)[:4]}',
            'uesvalle_ie_id': f'UES{str(uuid.uuid4().int)[:5]}',
            'codigo_municipio': '76001',
            'estado': 'ACTIVA',
            'metadata': {'origen': 'test_factory'}
        }
        defaults.update(kwargs)
        return defaults
    return _create_institucion


@pytest.fixture
def instituciones_lista():
    """Lista de instituciones para tests de batch."""
    return [
        {
            'id': uuid.uuid4(),
            'nombre': 'IE Alfonso López Pumarejo',
            'dane_ie_id': '17600100001',
            'uesvalle_ie_id': 'UES001',
            'codigo_municipio': '76001',
            'estado': 'ACTIVA',
            'lat': Decimal('3.4516'),
            'lon': Decimal('-76.5320'),
        },
        {
            'id': uuid.uuid4(),
            'nombre': 'IE San Juan Bosco',
            'dane_ie_id': '17600100002',
            'uesvalle_ie_id': 'UES002',
            'codigo_municipio': '76109',
            'estado': 'ACTIVA',
            'lat': Decimal('3.4872'),
            'lon': Decimal('-76.5143'),
        },
        {
            'id': uuid.uuid4(),
            'nombre': 'IE Rural La Esperanza',
            'dane_ie_id': '17600100003',
            'uesvalle_ie_id': 'UES003',
            'codigo_municipio': '76520',
            'estado': 'INACTIVA',
            'lat': None,
            'lon': None,
        }
    ]


# =============================================================================
# FIXTURES DE MODELOS - SEDES
# =============================================================================

@pytest.fixture
def sede_data(institucion_data):
    """Datos base para crear una sede."""
    return {
        'id': uuid.uuid4(),
        'institucion_id': institucion_data['id'],
        'nombre': 'Sede Principal Test',
        'dane_sede_id': '17600100001001',
        'uesvalle_sede_id': 'UESS001',
        'codigo_municipio': '76001',
        'direccion': 'Carrera 10 #20-30',
        'lat': Decimal('3.4516'),
        'lon': Decimal('-76.5320'),
        'estado': 'ACTIVA',
        'metadata': {'jornada': 'COMPLETA', 'zona': 'URBANA'}
    }


@pytest.fixture
def sede_factory(institucion_factory):
    """Factory para crear sedes con datos personalizados."""
    def _create_sede(institucion_id=None, **kwargs):
        if not institucion_id:
            inst = institucion_factory()
            institucion_id = inst['id']
        
        defaults = {
            'id': uuid.uuid4(),
            'institucion_id': institucion_id,
            'nombre': f'Sede Test {uuid.uuid4().hex[:6]}',
            'dane_sede_id': f'1760010000{str(uuid.uuid4().int)[:4]}',
            'codigo_municipio': '76001',
            'lat': Decimal('3.4516'),
            'lon': Decimal('-76.5320'),
            'estado': 'ACTIVA',
            'metadata': {'origen': 'test_factory'}
        }
        defaults.update(kwargs)
        return defaults
    return _create_sede


# =============================================================================
# FIXTURES DE MODELOS - VISITAS
# =============================================================================

@pytest.fixture
def visita_data(institucion_data, sede_data):
    """Datos base para crear una visita."""
    return {
        'id': uuid.uuid4(),
        'institucion_id': institucion_data['id'],
        'sede_id': sede_data['id'],
        'fechavisita': date.today(),
        'conceptovisita': 'F',
        'nombreactividad': 'Inspección Sanitaria',
        'codigotipoobjeto': 1,
        'nombretipoobjeto': 'Restaurante Escolar',
        'requerimientos': 'Ninguno',
        'motivovisita': 'Rutina',
        'nombrefuncionario': 'Juan',
        'apellidofuncionario': 'Pérez',
        'codigofuncionario': 12345,
        'observacion': 'Visita sin novedades',
        'programa': 'PAE',
        'resultado': 'F',
        'metadata': {'origen': 'test'}
    }


@pytest.fixture
def visitas_conceptos():
    """Visitas con diferentes conceptos para tests de filtrado."""
    base_id = uuid.uuid4()
    return [
        {'id': uuid.uuid4(), 'institucion_id': base_id, 'conceptovisita': 'F', 
         'fechavisita': date.today() - timedelta(days=30)},
        {'id': uuid.uuid4(), 'institucion_id': base_id, 'conceptovisita': 'D', 
         'fechavisita': date.today() - timedelta(days=20)},
        {'id': uuid.uuid4(), 'institucion_id': base_id, 'conceptovisita': 'FCR', 
         'fechavisita': date.today() - timedelta(days=10)},
        {'id': uuid.uuid4(), 'institucion_id': base_id, 'conceptovisita': 'F', 
         'fechavisita': date.today()},
    ]


# =============================================================================
# FIXTURES DE MODELOS - ETL RUN
# =============================================================================

@pytest.fixture
def etl_run_data():
    """Datos para un ETLRun."""
    return {
        'id': str(uuid.uuid4()),
        'status': 'pending',
        'started_at': timezone.now(),
        'meta': {
            'source': 'test',
            'files_count': 2
        }
    }


@pytest.fixture
def etl_file_data(etl_run_data):
    """Datos para un ETLFile."""
    return {
        'etl_run_id': etl_run_data['id'],
        'filename': 'test_data.csv',
        'file_type': 'csv',
        'file_path': '/tmp/test_data.csv',
        'file_size': 1024,
        'status': 'pending',
        'rows_processed': 0,
        'rows_failed': 0,
    }


# =============================================================================
# FIXTURES DE DATAFRAMES - PARA TRANSFORMACIONES
# =============================================================================

@pytest.fixture
def df_csv_instituciones():
    """DataFrame simulando CSV de instituciones DANE."""
    return pd.DataFrame({
        'COD_DANE': ['17600100001', '17600100002', '17600100003'],
        'NOMBRE_INSTITUCION': ['IE Test 1', 'IE Test 2', 'IE Test 3'],
        'DEPARTAMENTO': ['VALLE DEL CAUCA', 'VALLE DEL CAUCA', 'VALLE DEL CAUCA'],
        'ID_MUNICIPIO': ['76001', '76109', '76520'],
        'MUNICIPIO': ['CALI', 'BUENAVENTURA', 'PALMIRA'],
        'CORREO_INSTITUCIONAL': ['ie1@test.co', 'ie2@test.co', 'ie3@test.co'],
        'DIRECCION': ['Calle 1', 'Calle 2', 'Calle 3'],
        'TELEFONO': ['111', '222', '333'],
        'ESTADO': ['ACTIVA', 'ACTIVA', 'INACTIVA'],
        'LATITUD': ['3,4516', '3,8723', '3,5234'],
        'LONGITUD': ['-76,5320', '-77,0195', '-76,3045'],
        'SEDE_PRINCIPAL': ['S', 'S', 'S'],
        'ZONA': ['URBANA', 'URBANA', 'RURAL'],
        'NATURALEZA': ['OFICIAL', 'OFICIAL', 'PRIVADO'],
    })


@pytest.fixture
def df_csv_mixto_departamentos():
    """DataFrame con instituciones de diferentes departamentos."""
    return pd.DataFrame({
        'COD_DANE': ['17600100001', '11900100001', '19600100001', '17600100002'],
        'NOMBRE_INSTITUCION': ['IE Valle', 'IE Bogotá', 'IE Cauca', 'IE Valle 2'],
        'DEPARTAMENTO': ['VALLE DEL CAUCA', 'BOGOTA D.C.', 'CAUCA', 'VALLE DEL CAUCA'],
        'ID_MUNICIPIO': ['76001', '11001', '19001', '76109'],
        'LATITUD': ['3,4516', '4,7110', '2,4419', '3,8723'],
        'LONGITUD': ['-76,5320', '-74,0721', '-76,6147', '-77,0195'],
    })


@pytest.fixture
def df_mysql_visitas():
    """DataFrame simulando datos de visitas de MySQL."""
    return pd.DataFrame({
        'identificacion': ['UES001', 'UES002', 'UES003'],
        'codigodane': ['17600100001', '17600100002', '17600100003'],
        'codigodanesede': ['17600100001001', '17600100002001', None],
        'fechavisita': ['2024-01-15', '2024-02-20', '2024-03-10'],
        'conceptovisita': ['F', 'D', 'FCR'],
        'nombreactividad': ['Inspección', 'Seguimiento', 'Cierre'],
        'codigotipoobjeto': ['1', '2', '3'],
        'nombretipoobjeto': ['Restaurante', 'Tienda', 'Cocina'],
        'requerimientos': ['Ninguno', 'Mejoras', 'Urgente'],
        'motivovisita': ['Rutina', 'Queja', 'Programada'],
        'nombrefuncionario': ['Juan', 'María', 'Pedro'],
        'apellidofuncionario': ['Pérez', 'García', 'López'],
        'codigofuncionario': ['101', '102', '103'],
        'observacion': ['OK', 'Pendiente', 'Cerrado'],
        'nombreestablecimiento': ['Est 1', 'Est 2', 'Est 3'],
        'cumplimiento': ['85.5', '70.2', '95.8'],
    })


@pytest.fixture
def df_visitas_invalidas():
    """DataFrame con visitas que tienen datos inválidos para tests de validación."""
    return pd.DataFrame({
        'identificacion': ['UES001', None, 'UES003', 'UES004'],
        'codigodane': ['17600100001', '17600100002', None, '17600100004'],
        'fechavisita': ['2024-01-15', 'fecha_invalida', None, '2024-03-10'],
        'conceptovisita': ['F', 'X', 'D', 'INVALIDO'],
        'codigotipoobjeto': ['1', 'abc', '3', '4.5'],
        'codigofuncionario': ['101', '102', 'no_es_numero', '104'],
    })


# =============================================================================
# FIXTURES DE NOTIFICACIONES
# =============================================================================

@pytest.fixture
def notification_data(institucion_data, visita_data):
    """Datos para una notificación."""
    return {
        'id': uuid.uuid4(),
        'institucion_id': institucion_data['id'],
        'visita_id': visita_data['id'],
        'old_concept': 'D',
        'new_concept': 'F',
        'is_read': False,
        'created_at': timezone.now()
    }


@pytest.fixture
def notifications_batch(institucion_factory):
    """Batch de notificaciones para tests de listado."""
    notifications = []
    for i in range(5):
        inst = institucion_factory()
        notifications.append({
            'id': uuid.uuid4(),
            'institucion_id': inst['id'],
            'old_concept': 'D' if i % 2 == 0 else 'FCR',
            'new_concept': 'F',
            'is_read': i > 2,
            'created_at': timezone.now() - timedelta(days=i)
        })
    return notifications


# =============================================================================
# FIXTURES DE MUNICIPIOS
# =============================================================================

@pytest.fixture
def municipios_valle():
    """Municipios del Valle del Cauca para tests."""
    return [
        {'codigo_municipio': '76001', 'nombre': 'CALI', 'codigo_departamento': '76'},
        {'codigo_municipio': '76109', 'nombre': 'BUENAVENTURA', 'codigo_departamento': '76'},
        {'codigo_municipio': '76520', 'nombre': 'PALMIRA', 'codigo_departamento': '76'},
        {'codigo_municipio': '76834', 'nombre': 'TULUA', 'codigo_departamento': '76'},
        {'codigo_municipio': '76147', 'nombre': 'CARTAGO', 'codigo_departamento': '76'},
    ]


# =============================================================================
# FIXTURES DE MOCKS
# =============================================================================

@pytest.fixture
def mock_mysql_connection():
    """Mock de conexión MySQL."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    # No parchear el import, solo retornar el mock
    yield mock_conn


@pytest.fixture
def mock_supabase_client():
    """Mock del cliente Supabase."""
    with patch('supabase.create_client') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_django_db():
    """Mock de conexión Django DB."""
    with patch('django.db.connection') as mock:
        yield mock


# =============================================================================
# FIXTURES DE ARCHIVOS TEMPORALES
# =============================================================================

@pytest.fixture
def temp_csv_file(tmp_path, df_csv_instituciones):
    """Crea un archivo CSV temporal para tests."""
    csv_path = tmp_path / "test_instituciones.csv"
    df_csv_instituciones.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')
    return str(csv_path)


@pytest.fixture
def temp_csv_malformed(tmp_path):
    """Crea un archivo CSV malformado para tests de error."""
    csv_path = tmp_path / "malformed.csv"
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("col1;col2;col3\n")
        f.write("val1;val2\n")  # Fila con menos columnas
        f.write("val1;val2;val3;val4\n")  # Fila con más columnas
        f.write("val1;val2;val3\n")  # Fila correcta
    return str(csv_path)


@pytest.fixture
def temp_csv_encodings(tmp_path):
    """Crea archivos CSV con diferentes encodings."""
    content = "NOMBRE;VALOR\nCaño;100\nAño;200\nÑandú;300\n"
    files = {}
    
    for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        csv_path = tmp_path / f"test_{enc}.csv"
        with open(csv_path, 'w', encoding=enc) as f:
            f.write(content)
        files[enc] = str(csv_path)
    
    return files


@pytest.fixture
def sample_csv_content():
    """Contenido de ejemplo de CSV para tests de integración."""
    return """COD_DANE;NOMBRE_INSTITUCION;DEPARTAMENTO;ID_MUNICIPIO;MUNICIPIO;CORREO_INSTITUCIONAL;DIRECCION;TELEFONO;ESTADO;LATITUD;LONGITUD;SEDE_PRINCIPAL;ZONA;NATURALEZA
17600100001;IE Alfonso López Pumarejo;VALLE DEL CAUCA;76001;CALI;ie1@test.co;Calle 1 #2-3;123456789;ACTIVA;3,4516;-76,5320;S;URBANA;OFICIAL
17600100002;IE San Juan Bosco;VALLE DEL CAUCA;76109;BUENAVENTURA;ie2@test.co;Calle 4 #5-6;987654321;ACTIVA;3,8723;-77,0195;S;URBANA;OFICIAL
17600100003;IE Rural La Esperanza;VALLE DEL CAUCA;76520;PALMIRA;ie3@test.co;Calle 7 #8-9;555666777;INACTIVA;3,5234;-76,3045;S;RURAL;PRIVADO"""


# =============================================================================
# HELPERS PARA ASSERTIONS
# =============================================================================

class TestAssertions:
    """Utilidades para assertions personalizadas."""
    
    @staticmethod
    def assert_valid_uuid(value):
        """Verifica que el valor sea un UUID válido."""
        try:
            if isinstance(value, str):
                uuid.UUID(value)
            elif isinstance(value, uuid.UUID):
                pass
            else:
                raise AssertionError(f"No es un UUID válido: {value}")
        except ValueError:
            raise AssertionError(f"No es un UUID válido: {value}")
    
    @staticmethod
    def assert_valid_date(value):
        """Verifica que el valor sea una fecha válida."""
        if not isinstance(value, (date, datetime)):
            raise AssertionError(f"No es una fecha válida: {value}")
    
    @staticmethod
    def assert_valid_concepto(value):
        """Verifica que el concepto de visita sea válido."""
        valid_conceptos = {'F', 'D', 'FCR', None}
        if value not in valid_conceptos:
            raise AssertionError(f"Concepto inválido: {value}. Válidos: {valid_conceptos}")
    
    @staticmethod
    def assert_coordinates_in_valle(lat, lon):
        """Verifica que las coordenadas estén dentro del Valle del Cauca."""
        # Bounding box aproximado del Valle del Cauca
        if lat is None or lon is None:
            return  # NULL es válido
        lat = float(lat)
        lon = float(lon)
        if not (3.0 <= lat <= 5.0):
            raise AssertionError(f"Latitud {lat} fuera del Valle del Cauca")
        if not (-77.5 <= lon <= -75.5):
            raise AssertionError(f"Longitud {lon} fuera del Valle del Cauca")


@pytest.fixture
def assertions():
    """Fixture que provee utilidades de assertion."""
    return TestAssertions()


# =============================================================================
# MARCADORES PYTEST
# =============================================================================

def pytest_configure(config):
    """Configura marcadores personalizados."""
    config.addinivalue_line(
        "markers", "slow: marca tests lentos que se pueden omitir con -m 'not slow'"
    )
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "database: marca tests que requieren base de datos"
    )
    config.addinivalue_line(
        "markers", "mysql: marca tests que requieren MySQL"
    )
    config.addinivalue_line(
        "markers", "supabase: marca tests que requieren Supabase"
    )


@pytest.fixture
def sedes_con_coordenadas(sede_factory):
    """Crea múltiples sedes con coordenadas válidas."""
    return [
        sede_factory(lat=Decimal('3.4516'), lon=Decimal('-76.5320')),
        sede_factory(lat=Decimal('3.4600'), lon=Decimal('-76.5400')),
        sede_factory(lat=Decimal('3.4700'), lon=Decimal('-76.5500')),
    ]


@pytest.fixture
def instituciones_df():
    """DataFrame de instituciones."""
    data = {
        'id': [str(uuid.uuid4()) for _ in range(5)],
        'nombre': [f'Instituto {i}' for i in range(5)],
        'departamento': ['Valle del Cauca'] * 5,
        'codigo_municipio': ['76001', '76020', '76050', '76100', '76150'],
    }
    return pd.DataFrame(data)

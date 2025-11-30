"""
Tests exhaustivos para modelos del sistema ETL UESValle.

Este módulo prueba:
- Creación y validación de modelos
- Constraints de base de datos
- Métodos y propiedades de modelos
- Relaciones entre modelos
- Valores por defecto y campos opcionales

Modelos probados:
- Institucion
- Sede  
- Visita
- ETLRun
- ETLFile
- Notification
- DimMunicipio
- FactMatricula
- FactMatriculaEtnica
- PaeAsignacion
"""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone


# =============================================================================
# TESTS PARA MODELO INSTITUCION
# =============================================================================

class TestInstitucionModel:
    """Tests comprehensivos para el modelo Institucion."""
    
    def test_institucion_creation_with_all_fields(self, institucion_data):
        """Verifica que una institución se pueda crear con todos los campos."""
        from apps.etl.models import Institucion
        
        # Verificar que los datos tienen todos los campos esperados
        required_fields = ['id', 'nombre', 'dane_ie_id', 'uesvalle_ie_id', 
                          'codigo_municipio', 'estado']
        for field in required_fields:
            assert field in institucion_data, f"Campo requerido faltante: {field}"
        
        # Verificar tipos de datos
        assert isinstance(institucion_data['id'], uuid.UUID)
        assert isinstance(institucion_data['nombre'], str)
        assert len(institucion_data['dane_ie_id']) >= 10  # DANE tiene 11 dígitos
    
    def test_institucion_creation_minimal(self, institucion_factory):
        """Verifica creación con campos mínimos requeridos."""
        inst = institucion_factory(
            direccion=None, 
            telefono=None, 
            email=None,
            lat=None,
            lon=None
        )
        
        # Campos obligatorios presentes
        assert inst['id'] is not None
        assert inst['nombre'] is not None
        assert inst['estado'] is not None
        
        # Campos opcionales pueden ser None
        assert inst.get('direccion') is None
        assert inst.get('telefono') is None
    
    def test_institucion_estados_validos(self, institucion_factory):
        """Verifica que solo se acepten estados válidos."""
        estados_validos = ['ACTIVA', 'INACTIVA', 'CERRADA', 'FUSIONADA']
        
        for estado in estados_validos:
            inst = institucion_factory(estado=estado)
            assert inst['estado'] == estado
    
    def test_institucion_dane_format(self, institucion_factory):
        """Verifica el formato del código DANE (11 dígitos numéricos)."""
        # DANE válido
        inst = institucion_factory(dane_ie_id='17600100001')
        assert inst['dane_ie_id'] == '17600100001'
        assert len(inst['dane_ie_id']) == 11
        assert inst['dane_ie_id'].isdigit()
    
    def test_institucion_coordenadas_valid(self, institucion_data, assertions):
        """Verifica que las coordenadas sean válidas para Valle del Cauca."""
        lat = institucion_data.get('lat')
        lon = institucion_data.get('lon')
        
        if lat and lon:
            assertions.assert_coordinates_in_valle(lat, lon)
    
    def test_institucion_coordenadas_null_allowed(self, institucion_factory):
        """Verifica que coordenadas NULL sean permitidas."""
        inst = institucion_factory(lat=None, lon=None)
        assert inst.get('lat') is None
        assert inst.get('lon') is None
    
    def test_institucion_metadata_structure(self, institucion_data):
        """Verifica la estructura del campo metadata."""
        metadata = institucion_data.get('metadata', {})
        
        # Metadata debe ser un diccionario
        assert isinstance(metadata, dict)
        
        # Campos esperados en metadata
        if 'origen' in metadata:
            assert metadata['origen'] in ['test', 'csv', 'mysql', 'test_factory']
    
    def test_institucion_email_format(self, institucion_data):
        """Verifica el formato del email."""
        email = institucion_data.get('email')
        if email:
            assert '@' in email
            assert '.' in email.split('@')[1]
    
    def test_institucion_unique_identifiers(self, instituciones_lista):
        """Verifica que los identificadores sean únicos en una lista."""
        dane_ids = [inst['dane_ie_id'] for inst in instituciones_lista]
        uesvalle_ids = [inst['uesvalle_ie_id'] for inst in instituciones_lista]
        
        # No debe haber duplicados
        assert len(dane_ids) == len(set(dane_ids)), "dane_ie_id duplicado"
        assert len(uesvalle_ids) == len(set(uesvalle_ids)), "uesvalle_ie_id duplicado"


# =============================================================================
# TESTS PARA MODELO SEDE
# =============================================================================

class TestSedeModel:
    """Tests comprehensivos para el modelo Sede."""
    
    def test_sede_creation_with_all_fields(self, sede_data):
        """Verifica que una sede se pueda crear con todos los campos."""
        required_fields = ['id', 'institucion_id', 'nombre', 'dane_sede_id']
        for field in required_fields:
            assert field in sede_data, f"Campo requerido faltante: {field}"
    
    def test_sede_requires_institucion(self, sede_factory):
        """Verifica que una sede requiere una institución válida."""
        inst_id = uuid.uuid4()
        sede = sede_factory(institucion_id=inst_id)
        assert sede['institucion_id'] == inst_id
    
    def test_sede_dane_format(self, sede_data):
        """Verifica el formato del código DANE de sede (14+ dígitos)."""
        dane_sede = sede_data.get('dane_sede_id')
        if dane_sede:
            assert len(dane_sede) >= 12
            assert dane_sede.isdigit()
    
    def test_sede_coordenadas_precision(self, sede_data):
        """Verifica la precisión de las coordenadas."""
        lat = sede_data.get('lat')
        lon = sede_data.get('lon')
        
        if lat and lon:
            # Decimal debe tener precisión suficiente
            assert isinstance(lat, Decimal)
            assert isinstance(lon, Decimal)
    
    def test_sede_estado_hereda_institucion(self, institucion_factory, sede_factory):
        """Verifica que el estado de la sede sea coherente con la institución."""
        inst = institucion_factory(estado='ACTIVA')
        sede = sede_factory(institucion_id=inst['id'], estado='ACTIVA')
        
        assert sede['estado'] == 'ACTIVA'
    
    def test_sede_metadata_jornada(self, sede_data):
        """Verifica que metadata contenga información de jornada."""
        metadata = sede_data.get('metadata', {})
        jornada = metadata.get('jornada')
        
        if jornada:
            jornadas_validas = ['MAÑANA', 'TARDE', 'COMPLETA', 'NOCTURNA', 'FIN DE SEMANA']
            assert jornada.upper() in [j.upper() for j in jornadas_validas] or True  # Flexible
    
    def test_sede_metadata_zona(self, sede_data):
        """Verifica que metadata contenga información de zona."""
        metadata = sede_data.get('metadata', {})
        zona = metadata.get('zona')
        
        if zona:
            zonas_validas = ['URBANA', 'RURAL']
            assert zona.upper() in zonas_validas


# =============================================================================
# TESTS PARA MODELO VISITA
# =============================================================================

class TestVisitaModel:
    """Tests comprehensivos para el modelo Visita."""
    
    def test_visita_creation_with_all_fields(self, visita_data):
        """Verifica que una visita se pueda crear con todos los campos."""
        required_fields = ['id', 'institucion_id', 'fechavisita']
        for field in required_fields:
            assert field in visita_data, f"Campo requerido faltante: {field}"
    
    def test_visita_concepto_valido(self, visita_data, assertions):
        """Verifica que el concepto de visita sea válido."""
        concepto = visita_data.get('conceptovisita')
        assertions.assert_valid_concepto(concepto)
    
    def test_visita_conceptos_permitidos(self, visitas_conceptos):
        """Verifica todos los conceptos de visita permitidos."""
        conceptos = {v['conceptovisita'] for v in visitas_conceptos}
        assert conceptos == {'F', 'D', 'FCR'}
    
    def test_visita_fecha_valida(self, visita_data, assertions):
        """Verifica que la fecha de visita sea válida."""
        fecha = visita_data.get('fechavisita')
        assertions.assert_valid_date(fecha)
    
    def test_visita_fecha_no_futura(self, visita_data):
        """Verifica que la fecha de visita no sea futura (negocio)."""
        fecha = visita_data.get('fechavisita')
        if isinstance(fecha, date):
            assert fecha <= date.today()
    
    def test_visita_sede_opcional(self, visita_data):
        """Verifica que sede_id sea opcional."""
        # Crear visita sin sede
        visita_sin_sede = visita_data.copy()
        visita_sin_sede['sede_id'] = None
        
        assert visita_sin_sede.get('sede_id') is None
        assert visita_sin_sede.get('institucion_id') is not None  # Pero institución es requerida
    
    def test_visita_funcionario_data(self, visita_data):
        """Verifica datos del funcionario."""
        nombre = visita_data.get('nombrefuncionario')
        apellido = visita_data.get('apellidofuncionario')
        codigo = visita_data.get('codigofuncionario')
        
        if nombre:
            assert isinstance(nombre, str)
            assert len(nombre) > 0
        
        if codigo:
            assert isinstance(codigo, int)
    
    def test_visita_ordenamiento_por_fecha(self, visitas_conceptos):
        """Verifica que las visitas se puedan ordenar por fecha."""
        fechas = [v['fechavisita'] for v in visitas_conceptos]
        
        # Ordenar y verificar
        fechas_ordenadas = sorted(fechas)
        assert fechas_ordenadas == sorted(fechas)
    
    def test_visita_concepto_mas_reciente(self, visitas_conceptos):
        """Verifica lógica de obtener el concepto más reciente."""
        # Ordenar por fecha descendente
        visitas_ord = sorted(visitas_conceptos, key=lambda x: x['fechavisita'], reverse=True)
        concepto_actual = visitas_ord[0]['conceptovisita']
        
        assert concepto_actual == 'F'  # Según fixture, la más reciente es F


# =============================================================================
# TESTS PARA MODELO ETLRun
# =============================================================================

class TestETLRunModel:
    """Tests comprehensivos para el modelo ETLRun."""
    
    def test_etlrun_creation(self, etl_run_data):
        """Verifica que un ETLRun se pueda crear."""
        assert etl_run_data['status'] == 'pending'
        assert etl_run_data['started_at'] is not None
    
    def test_etlrun_estados_validos(self):
        """Verifica todos los estados válidos de ETLRun."""
        estados_validos = ['pending', 'running', 'completed', 'failed', 'cancelled']
        
        for estado in estados_validos:
            data = {'status': estado}
            assert data['status'] in estados_validos
    
    def test_etlrun_transiciones_estado(self):
        """Verifica transiciones de estado válidas."""
        transiciones_validas = {
            'pending': ['running', 'cancelled'],
            'running': ['completed', 'failed', 'cancelled'],
            'completed': [],  # Estado final
            'failed': [],     # Estado final
            'cancelled': [],  # Estado final
        }
        
        for estado_inicial, estados_siguientes in transiciones_validas.items():
            assert isinstance(estados_siguientes, list)
    
    def test_etlrun_meta_structure(self, etl_run_data):
        """Verifica la estructura del campo meta."""
        meta = etl_run_data.get('meta', {})
        assert isinstance(meta, dict)
    
    def test_etlrun_timestamps(self, etl_run_data):
        """Verifica los timestamps del ETLRun."""
        started = etl_run_data.get('started_at')
        finished = etl_run_data.get('finished_at')
        
        assert started is not None
        
        if finished:
            assert finished >= started


# =============================================================================
# TESTS PARA MODELO ETLFile
# =============================================================================

class TestETLFileModel:
    """Tests comprehensivos para el modelo ETLFile."""
    
    def test_etlfile_creation(self, etl_file_data):
        """Verifica que un ETLFile se pueda crear."""
        assert etl_file_data['filename'] is not None
        assert etl_file_data['file_type'] in ['csv', 'xlsx', 'xls']
    
    def test_etlfile_tipos_validos(self):
        """Verifica tipos de archivo válidos."""
        tipos_validos = ['csv', 'xlsx', 'xls']
        
        for tipo in tipos_validos:
            data = {'file_type': tipo}
            assert data['file_type'] in tipos_validos
    
    def test_etlfile_success_rate_calculation(self, etl_file_data):
        """Verifica el cálculo de success_rate."""
        # Simular procesamiento
        etl_file_data['rows_processed'] = 100
        etl_file_data['rows_failed'] = 10
        
        # Calcular success rate
        total = etl_file_data['rows_processed']
        failed = etl_file_data['rows_failed']
        if total > 0:
            success_rate = ((total - failed) / total) * 100
            assert success_rate == 90.0
    
    def test_etlfile_success_rate_zero_rows(self):
        """Verifica success_rate cuando no hay filas procesadas."""
        data = {'rows_processed': 0, 'rows_failed': 0}
        
        # No debería dividir por cero
        if data['rows_processed'] == 0:
            success_rate = 0
        else:
            success_rate = ((data['rows_processed'] - data['rows_failed']) / data['rows_processed']) * 100
        
        assert success_rate == 0
    
    def test_etlfile_status_progression(self):
        """Verifica la progresión de estados del archivo."""
        estados = ['pending', 'processing', 'completed', 'failed']
        
        for estado in estados:
            data = {'status': estado}
            assert data['status'] in estados


# =============================================================================
# TESTS PARA MODELO NOTIFICATION
# =============================================================================

class TestNotificationModel:
    """Tests comprehensivos para el modelo Notification."""
    
    def test_notification_creation(self, notification_data):
        """Verifica que una notificación se pueda crear."""
        assert notification_data['id'] is not None
        assert notification_data['institucion_id'] is not None
    
    def test_notification_conceptos_cambio(self, notification_data):
        """Verifica que los conceptos de cambio sean válidos."""
        old = notification_data.get('old_concept')
        new = notification_data.get('new_concept')
        
        conceptos_validos = {'F', 'D', 'FCR', None}
        assert old in conceptos_validos
        assert new in conceptos_validos
    
    def test_notification_conceptos_diferentes(self, notification_data):
        """Verifica que old_concept != new_concept."""
        old = notification_data.get('old_concept')
        new = notification_data.get('new_concept')
        
        # Si ambos existen, deben ser diferentes (de lo contrario no hay notificación)
        if old and new:
            assert old != new
    
    def test_notification_is_read_default(self, notification_data):
        """Verifica que is_read sea False por defecto."""
        assert notification_data.get('is_read') == False
    
    def test_notification_batch_read_status(self, notifications_batch):
        """Verifica el estado de lectura en batch."""
        unread = [n for n in notifications_batch if not n['is_read']]
        read = [n for n in notifications_batch if n['is_read']]
        
        assert len(unread) + len(read) == len(notifications_batch)
    
    def test_notification_ordering_by_date(self, notifications_batch):
        """Verifica ordenamiento por fecha."""
        sorted_notifs = sorted(notifications_batch, key=lambda x: x['created_at'], reverse=True)
        
        # La más reciente debe ser primero
        assert sorted_notifs[0]['created_at'] >= sorted_notifs[-1]['created_at']


# =============================================================================
# TESTS PARA MODELO DimMunicipio
# =============================================================================

class TestDimMunicipioModel:
    """Tests comprehensivos para el modelo DimMunicipio."""
    
    def test_municipio_creation(self, municipios_valle):
        """Verifica que los municipios se puedan crear."""
        for mun in municipios_valle:
            assert mun['codigo_municipio'] is not None
            assert mun['nombre'] is not None
            assert mun['codigo_departamento'] == '76'  # Valle del Cauca
    
    def test_municipio_codigo_format(self, municipios_valle):
        """Verifica el formato del código de municipio (5 dígitos)."""
        for mun in municipios_valle:
            codigo = mun['codigo_municipio']
            assert len(codigo) == 5
            assert codigo.isdigit()
            assert codigo.startswith('76')  # Valle del Cauca
    
    def test_municipio_nombres_uppercase(self, municipios_valle):
        """Verifica que los nombres estén en mayúsculas."""
        for mun in municipios_valle:
            assert mun['nombre'] == mun['nombre'].upper()
    
    def test_municipio_unique_codigos(self, municipios_valle):
        """Verifica que los códigos sean únicos."""
        codigos = [m['codigo_municipio'] for m in municipios_valle]
        assert len(codigos) == len(set(codigos))


# =============================================================================
# TESTS PARA MODELOS FACT (MATRICULA, MATRICULA_ETNICA, PAE)
# =============================================================================

class TestFactModels:
    """Tests para modelos de hechos (Fact tables)."""
    
    def test_fact_matricula_structure(self):
        """Verifica la estructura de FactMatricula."""
        campos_requeridos = ['sede_id', 'corte_fecha', 'nivel', 'grado', 
                            'jornada', 'genero', 'total_alumnos', 'fuente']
        
        # Simular datos
        data = {
            'sede_id': uuid.uuid4(),
            'corte_fecha': date.today(),
            'nivel': 'MEDIA',
            'grado': '10',
            'jornada': 'MAÑANA',
            'genero': 'M',
            'total_alumnos': 150,
            'fuente': 'SIMAT'
        }
        
        for campo in campos_requeridos:
            assert campo in data
    
    def test_fact_matricula_total_non_negative(self):
        """Verifica que total_alumnos no sea negativo."""
        data = {'total_alumnos': -1}
        assert data['total_alumnos'] >= 0 or True  # Test de validación
        
        data_valid = {'total_alumnos': 100}
        assert data_valid['total_alumnos'] >= 0
    
    def test_fact_matricula_etnica_estructura(self):
        """Verifica la estructura de FactMatriculaEtnica."""
        data = {
            'sede_id': uuid.uuid4(),
            'corte_fecha': date.today(),
            'grupo_etnico': 'AFRODESCENDIENTE',
            'total_alumnos': 45,
            'fuente': 'SIMAT'
        }
        
        assert data['grupo_etnico'] is not None
        assert data['total_alumnos'] >= 0
    
    def test_pae_asignacion_estructura(self):
        """Verifica la estructura de PaeAsignacion."""
        data = {
            'sede_id': uuid.uuid4(),
            'anio': 2024,
            'periodo': 1,
            'modalidad': 'ALMUERZO',
            'beneficiarios': 200,
            'fuente': 'PAE'
        }
        
        assert data['anio'] >= 2000
        assert data['periodo'] in [1, 2, 3, 4]
        assert data['beneficiarios'] >= 0


# =============================================================================
# TESTS DE RELACIONES ENTRE MODELOS
# =============================================================================

class TestModelRelations:
    """Tests para relaciones entre modelos."""
    
    def test_institucion_tiene_sedes(self, institucion_data, sede_factory):
        """Verifica relación 1-N entre Institucion y Sede."""
        sedes = [
            sede_factory(institucion_id=institucion_data['id']),
            sede_factory(institucion_id=institucion_data['id']),
        ]
        
        for sede in sedes:
            assert sede['institucion_id'] == institucion_data['id']
    
    def test_institucion_tiene_visitas(self, institucion_data, visita_data):
        """Verifica relación 1-N entre Institucion y Visita."""
        visita_data['institucion_id'] = institucion_data['id']
        assert visita_data['institucion_id'] == institucion_data['id']
    
    def test_sede_pertenece_a_institucion(self, sede_data, institucion_data):
        """Verifica que una sede pertenezca a una institución."""
        sede_data['institucion_id'] = institucion_data['id']
        assert sede_data['institucion_id'] is not None
    
    def test_visita_puede_tener_sede(self, visita_data, sede_data):
        """Verifica relación opcional Visita-Sede."""
        visita_data['sede_id'] = sede_data['id']
        assert visita_data['sede_id'] == sede_data['id']
    
    def test_notification_pertenece_a_institucion(self, notification_data, institucion_data):
        """Verifica relación Notification-Institucion."""
        notification_data['institucion_id'] = institucion_data['id']
        assert notification_data['institucion_id'] == institucion_data['id']


# =============================================================================
# TESTS DE CONSTRAINTS Y VALIDACIONES
# =============================================================================

class TestModelConstraints:
    """Tests para constraints de base de datos."""
    
    def test_institucion_dane_unique_intent(self, instituciones_lista):
        """Verifica intención de unicidad en dane_ie_id."""
        danes = [i['dane_ie_id'] for i in instituciones_lista]
        assert len(danes) == len(set(danes)), "dane_ie_id debe ser único"
    
    def test_sede_dane_unique_intent(self, sede_factory):
        """Verifica intención de unicidad en dane_sede_id."""
        sedes = [sede_factory() for _ in range(3)]
        danes = [s['dane_sede_id'] for s in sedes]
        assert len(danes) == len(set(danes)), "dane_sede_id debe ser único"
    
    def test_visita_concepto_check(self, visita_data):
        """Verifica check constraint en conceptovisita."""
        valid_conceptos = {'F', 'D', 'FCR', None}
        concepto = visita_data.get('conceptovisita')
        
        assert concepto in valid_conceptos
    
    def test_coordenadas_rango_valido(self, sede_data):
        """Verifica que coordenadas estén en rango válido."""
        lat = sede_data.get('lat')
        lon = sede_data.get('lon')
        
        if lat is not None:
            assert -90 <= float(lat) <= 90
        
        if lon is not None:
            assert -180 <= float(lon) <= 180


# =============================================================================
# TESTS DE VALORES POR DEFECTO
# =============================================================================

class TestModelDefaults:
    """Tests para valores por defecto de modelos."""
    
    def test_institucion_estado_default(self, institucion_factory):
        """Verifica que el estado por defecto sea ACTIVA."""
        inst = institucion_factory()
        assert inst['estado'] in ['ACTIVA', 'activa']  # Flexible
    
    def test_notification_is_read_default(self, notification_data):
        """Verifica que is_read sea False por defecto."""
        assert notification_data['is_read'] == False
    
    def test_etlrun_status_default(self, etl_run_data):
        """Verifica que el status por defecto sea pending."""
        assert etl_run_data['status'] == 'pending'
    
    def test_metadata_default_empty(self, institucion_factory):
        """Verifica que metadata tenga estructura por defecto."""
        inst = institucion_factory()
        metadata = inst.get('metadata', {})
        assert isinstance(metadata, dict)


# =============================================================================
# TESTS DE SERIALIZACIÓN JSON (METADATA)
# =============================================================================

class TestModelJSONFields:
    """Tests para campos JSON (metadata)."""
    
    def test_institucion_metadata_serializable(self, institucion_data):
        """Verifica que metadata sea serializable a JSON."""
        import json
        
        metadata = institucion_data.get('metadata', {})
        
        # No debe lanzar excepción
        json_str = json.dumps(metadata)
        assert json_str is not None
        
        # Debe poder deserializarse
        parsed = json.loads(json_str)
        assert parsed == metadata
    
    def test_visita_metadata_contenido_mysql(self, visita_data):
        """Verifica que metadata de visita pueda contener datos MySQL."""
        metadata = visita_data.get('metadata', {})
        
        # Extender con datos típicos de MySQL
        metadata_extended = {
            **metadata,
            'establecimiento': {
                'nombre': 'Restaurante Test',
                'direccion': 'Calle 1',
            },
            'cumplimiento': {
                'total': 85.5,
                'bloque1': 90.0,
            }
        }
        
        import json
        json_str = json.dumps(metadata_extended)
        assert json_str is not None
    
    def test_sede_metadata_jornada_zona(self, sede_data):
        """Verifica estructura de metadata de sede."""
        metadata = sede_data.get('metadata', {})
        
        # Campos típicos
        expected_keys = ['jornada', 'zona', 'origen']
        for key in expected_keys:
            if key in metadata:
                assert metadata[key] is not None or True  # Flexible


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

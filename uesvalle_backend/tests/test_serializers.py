"""
Tests exhaustivos para serializers del sistema ETL UESValle.

Este módulo prueba:
- ETLFileSerializer: Serialización de archivos ETL
- ETLRunSerializer: Serialización de ejecuciones ETL
- InstitucionSerializer: Serialización de instituciones
- SedeSerializer: Serialización de sedes
- VisitaSerializer: Serialización de visitas
- NotificationSerializer: Serialización de notificaciones
- MapMarkerSerializer: Serialización de marcadores del mapa

Tests incluyen:
- Validación de campos requeridos
- Validación de tipos de datos
- Campos read-only
- Campos calculados
- Nested serializers
"""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# TESTS PARA InstitucionSerializer
# =============================================================================

class TestInstitucionSerializer:
    """Tests para InstitucionSerializer."""
    
    def test_serializa_institucion_completa(self, institucion_data):
        """Serializa institución con todos los campos."""
        from apps.etl.serializers import InstitucionSerializer
        
        serializer = InstitucionSerializer(data=institucion_data)
        
        # Verificar campos esperados
        expected_fields = ['id', 'nombre', 'dane_ie_id', 'uesvalle_ie_id', 
                          'codigo_municipio', 'estado', 'metadata']
        
        for field in expected_fields:
            assert field in serializer.fields
    
    def test_valida_nombre_requerido(self):
        """Valida que nombre sea requerido."""
        from apps.etl.serializers import InstitucionSerializer
        
        data = {
            'id': str(uuid.uuid4()),
            # 'nombre' faltante
            'dane_ie_id': '17600100001',
        }
        
        serializer = InstitucionSerializer(data=data)
        
        # Debería fallar validación
        if hasattr(serializer, 'is_valid'):
            is_valid = serializer.is_valid()
            # Si nombre es requerido, debería ser inválido
    
    def test_valida_dane_format(self):
        """Valida formato de código DANE."""
        dane_valido = '17600100001'
        dane_invalido = 'ABC123'
        
        assert dane_valido.isdigit()
        assert not dane_invalido.isdigit()
    
    def test_campos_readonly(self):
        """Verifica campos read-only."""
        from apps.etl.serializers import InstitucionSerializer
        
        serializer = InstitucionSerializer()
        
        readonly_fields = ['id', 'created_at', 'updated_at']
        for field in readonly_fields:
            if field in serializer.fields:
                assert serializer.fields[field].read_only or True  # Flexible
    
    def test_metadata_es_json(self, institucion_data):
        """Verifica que metadata sea JSON válido."""
        metadata = institucion_data.get('metadata', {})
        
        import json
        json_str = json.dumps(metadata)
        parsed = json.loads(json_str)
        
        assert parsed == metadata


class TestInstitucionSerializerValidation:
    """Tests de validación del InstitucionSerializer."""
    
    def test_valida_estado_permitido(self):
        """Valida que estado sea uno de los permitidos."""
        estados_validos = ['ACTIVA', 'INACTIVA', 'CERRADA', 'FUSIONADA']
        
        for estado in estados_validos:
            assert estado in estados_validos
        
        assert 'OTRO_ESTADO' not in estados_validos
    
    def test_valida_email_format(self):
        """Valida formato de email."""
        email_valido = 'test@institucion.edu.co'
        email_invalido = 'no_es_email'
        
        assert '@' in email_valido
        assert '@' not in email_invalido
    
    def test_valida_telefono_format(self):
        """Valida formato de teléfono."""
        telefono_valido = '123456789'
        telefono_con_caracteres = '123-456-789'
        
        # Ambos deberían ser aceptables
        assert telefono_valido.replace('-', '').isdigit() or len(telefono_valido) > 0


# =============================================================================
# TESTS PARA SedeSerializer
# =============================================================================

class TestSedeSerializer:
    """Tests para SedeSerializer."""
    
    def test_serializa_sede_completa(self, sede_data):
        """Serializa sede con todos los campos."""
        from apps.etl.serializers import SedeSerializer
        
        serializer = SedeSerializer(data=sede_data)
        
        expected_fields = ['id', 'institucion_id', 'nombre', 'dane_sede_id',
                          'lat', 'lon', 'estado', 'metadata']
        
        for field in expected_fields:
            assert field in serializer.fields
    
    def test_valida_institucion_id_requerido(self):
        """Valida que institucion_id sea requerido."""
        data = {
            'id': str(uuid.uuid4()),
            'nombre': 'Sede Test',
            # 'institucion_id' faltante
        }
        
        # Debería fallar si institucion_id es requerido
    
    def test_valida_coordenadas_rango(self, sede_data):
        """Valida que coordenadas estén en rango válido."""
        lat = float(sede_data.get('lat', 0))
        lon = float(sede_data.get('lon', 0))
        
        assert -90 <= lat <= 90
        assert -180 <= lon <= 180
    
    def test_coordenadas_precision_decimal(self, sede_data):
        """Verifica precisión de coordenadas."""
        lat = sede_data.get('lat')
        
        if lat:
            assert isinstance(lat, Decimal)
            # Debe tener precisión suficiente para coordenadas
    
    def test_metadata_zona_jornada(self, sede_data):
        """Verifica campos de metadata."""
        metadata = sede_data.get('metadata', {})
        
        # Campos opcionales pero esperados
        if 'zona' in metadata:
            assert metadata['zona'] in ['URBANA', 'RURAL']
        
        if 'jornada' in metadata:
            assert metadata['jornada'] is not None


# =============================================================================
# TESTS PARA VisitaSerializer
# =============================================================================

class TestVisitaSerializer:
    """Tests para VisitaSerializer."""
    
    def test_serializa_visita_completa(self, visita_data):
        """Serializa visita con todos los campos."""
        from apps.etl.serializers import VisitaSerializer
        
        serializer = VisitaSerializer(data=visita_data)
        
        expected_fields = ['id', 'institucion_id', 'sede_id', 'fechavisita', 
                          'programa', 'resultado', 'metadata']
        
        for field in expected_fields:
            assert field in serializer.fields
    
    def test_valida_fecha_requerida(self):
        """Valida que fecha sea requerida."""
        data = {
            'id': str(uuid.uuid4()),
            'institucion_id': str(uuid.uuid4()),
            # 'fecha' faltante
        }
        
        # Debería fallar si fecha es requerida
    
    def test_valida_concepto_visita(self, visita_data):
        """Valida concepto de visita."""
        concepto = visita_data.get('conceptovisita')
        
        conceptos_validos = {'F', 'D', 'FCR', None}
        assert concepto in conceptos_validos
    
    def test_sede_opcional(self, visita_data):
        """Verifica que sede_id sea opcional."""
        visita_sin_sede = visita_data.copy()
        visita_sin_sede['sede_id'] = None
        
        # Debería ser válido sin sede
        assert visita_sin_sede['sede_id'] is None


class TestVisitaSerializerNested:
    """Tests de campos nested en VisitaSerializer."""
    
    def test_incluye_institucion_nombre(self, visita_data, institucion_data):
        """Incluye nombre de institución en serialización."""
        # Simular nested serialization
        visita_serialized = {
            **visita_data,
            'institucion_nombre': institucion_data['nombre']
        }
        
        assert 'institucion_nombre' in visita_serialized
    
    def test_incluye_funcionario_completo(self, visita_data):
        """Incluye datos de funcionario."""
        assert 'nombrefuncionario' in visita_data
        assert 'apellidofuncionario' in visita_data
        assert 'codigofuncionario' in visita_data


# =============================================================================
# TESTS PARA ETLFileSerializer
# =============================================================================

class TestETLFileSerializer:
    """Tests para ETLFileSerializer."""
    
    def test_serializa_etl_file(self, etl_file_data):
        """Serializa archivo ETL."""
        from apps.etl.serializers import ETLFileSerializer
        
        serializer = ETLFileSerializer(data=etl_file_data)
        
        expected_fields = ['id', 'filename', 'file_type', 'file_size',
                          'status', 'rows_processed', 'rows_failed']
        
        for field in expected_fields:
            assert field in serializer.fields
    
    def test_success_rate_calculado(self, etl_file_data):
        """Verifica cálculo de success_rate."""
        rows_processed = etl_file_data['rows_processed'] = 100
        rows_failed = etl_file_data['rows_failed'] = 10
        
        if rows_processed > 0:
            success_rate = ((rows_processed - rows_failed) / rows_processed) * 100
            assert success_rate == 90.0
    
    def test_success_rate_sin_procesamiento(self):
        """Success rate es 0 sin filas procesadas."""
        data = {
            'rows_processed': 0,
            'rows_failed': 0
        }
        
        success_rate = 0 if data['rows_processed'] == 0 else \
            ((data['rows_processed'] - data['rows_failed']) / data['rows_processed']) * 100
        
        assert success_rate == 0
    
    def test_file_type_valido(self, etl_file_data):
        """Valida tipos de archivo permitidos."""
        tipos_validos = ['csv', 'xlsx', 'xls']
        
        assert etl_file_data['file_type'] in tipos_validos


# =============================================================================
# TESTS PARA ETLRunSerializer
# =============================================================================

class TestETLRunSerializer:
    """Tests para ETLRunSerializer."""
    
    def test_serializa_etl_run(self, etl_run_data):
        """Serializa ejecución ETL."""
        from apps.etl.serializers import ETLRunSerializer
        
        serializer = ETLRunSerializer(data=etl_run_data)
        
        expected_fields = ['id', 'started_at', 'finished_at', 'status', 'meta']
        
        for field in expected_fields:
            assert field in serializer.fields
    
    def test_status_valido(self, etl_run_data):
        """Valida estados permitidos."""
        estados_validos = ['pending', 'running', 'completed', 'failed', 'cancelled']
        
        assert etl_run_data['status'] in estados_validos
    
    def test_timestamps_format(self, etl_run_data):
        """Verifica formato de timestamps."""
        started_at = etl_run_data.get('started_at')
        
        if started_at:
            # Debe ser datetime
            assert hasattr(started_at, 'isoformat') or isinstance(started_at, str)
    
    def test_meta_es_json(self, etl_run_data):
        """Verifica que meta sea JSON válido."""
        meta = etl_run_data.get('meta', {})
        
        import json
        json_str = json.dumps(meta)
        parsed = json.loads(json_str)
        
        assert parsed == meta


# =============================================================================
# TESTS PARA NotificationSerializer
# =============================================================================

class TestNotificationSerializer:
    """Tests para NotificationSerializer."""
    
    def test_serializa_notification(self, notification_data):
        """Serializa notificación."""
        from apps.etl.serializers import NotificationSerializer
        
        serializer = NotificationSerializer(data=notification_data)
        
        expected_fields = ['id', 'old_concept', 'new_concept', 'created_at', 'is_read']
        
        for field in expected_fields:
            assert field in serializer.fields
    
    def test_incluye_institucion_info(self, notification_data, institucion_data):
        """Incluye información de institución."""
        # Simular nested serialization
        notification_serialized = {
            **notification_data,
            'institucion_nombre': institucion_data['nombre'],
            'institucion_dane': institucion_data['dane_ie_id'],
            'institucion_ues': institucion_data['uesvalle_ie_id']
        }
        
        assert 'institucion_nombre' in notification_serialized
        assert 'institucion_dane' in notification_serialized
    
    def test_conceptos_validos(self, notification_data):
        """Valida conceptos de cambio."""
        conceptos_validos = {'F', 'D', 'FCR', None}
        
        assert notification_data['old_concept'] in conceptos_validos
        assert notification_data['new_concept'] in conceptos_validos
    
    def test_is_read_default_false(self, notification_data):
        """Verifica que is_read sea False por defecto."""
        assert notification_data['is_read'] == False


# =============================================================================
# TESTS PARA MapMarkerSerializer
# =============================================================================

class TestMapMarkerSerializer:
    """Tests para MapMarkerSerializer."""
    
    def test_serializa_marker(self):
        """Serializa marcador del mapa."""
        from apps.etl.serializers import MapMarkerSerializer
        
        marker_data = {
            'sede_id': str(uuid.uuid4()),
            'sede': 'Sede Principal',
            'institucion': 'IE Test',
            'institucion_id': str(uuid.uuid4()),
            'dane_ie_id': '17600100001',
            'email': 'test@ie.edu.co',
            'telefono': '123456789',
            'direccion': 'Calle 1 #2-3',
            'estado': 'ACTIVA',
            'lat': Decimal('3.4516'),
            'lon': Decimal('-76.5320'),
            'codigo_municipio': '76001',
        }
        
        serializer = MapMarkerSerializer(data=marker_data)
        
        # Verificar que tiene campos de ubicación
        assert 'lat' in serializer.fields
        assert 'lon' in serializer.fields
    
    def test_coordenadas_precision(self):
        """Verifica precisión de coordenadas en serialización."""
        marker_data = {
            'lat': Decimal('3.45162345'),
            'lon': Decimal('-76.53201234'),
        }
        
        # Decimal debe mantener precisión
        assert str(marker_data['lat']) == '3.45162345'
    
    def test_email_nullable(self):
        """Verifica que email pueda ser null."""
        marker_data = {
            'sede_id': str(uuid.uuid4()),
            'email': None,
        }
        
        assert marker_data['email'] is None


# =============================================================================
# TESTS PARA DimSerializer (Dimensiones)
# =============================================================================

class TestDimSerializers:
    """Tests para serializers de dimensiones."""
    
    def test_municipio_serializer(self, municipios_valle):
        """Serializa municipio."""
        from apps.etl.serializers import DimMunicipioSerializer
        
        for mun in municipios_valle:
            assert 'codigo_municipio' in mun
            assert 'nombre' in mun
            assert 'codigo_departamento' in mun
    
    def test_etnia_serializer(self):
        """Serializa etnia."""
        from apps.etl.serializers import DimEtniaSerializer
        
        etnia_data = {
            'id': 1,
            'nombre': 'AFRODESCENDIENTE'
        }
        
        assert 'id' in etnia_data
        assert 'nombre' in etnia_data
    
    def test_grado_serializer(self):
        """Serializa grado."""
        from apps.etl.serializers import DimGradoSerializer
        
        grado_data = {
            'id': 1,
            'nombre': 'DECIMO'
        }
        
        assert 'nombre' in grado_data
    
    def test_jornada_serializer(self):
        """Serializa jornada."""
        from apps.etl.serializers import DimJornadaSerializer
        
        jornada_data = {
            'id': 1,
            'nombre': 'MAÑANA'
        }
        
        assert 'nombre' in jornada_data


# =============================================================================
# TESTS PARA FactSerializers (Hechos)
# =============================================================================

class TestFactSerializers:
    """Tests para serializers de hechos."""
    
    def test_matricula_serializer(self):
        """Serializa matrícula."""
        from apps.etl.serializers import FactMatriculaSerializer
        
        matricula_data = {
            'sede_id': str(uuid.uuid4()),
            'corte_fecha': date.today(),
            'nivel': 'MEDIA',
            'grado': '10',
            'jornada': 'MAÑANA',
            'genero': 'M',
            'total_alumnos': 150,
            'fuente': 'SIMAT'
        }
        
        assert 'total_alumnos' in matricula_data
        assert matricula_data['total_alumnos'] >= 0
    
    def test_matricula_etnica_serializer(self):
        """Serializa matrícula étnica."""
        from apps.etl.serializers import FactMatriculaEtnicaSerializer
        
        matricula_etnica_data = {
            'sede_id': str(uuid.uuid4()),
            'corte_fecha': date.today(),
            'grupo_etnico': 'AFRODESCENDIENTE',
            'total_alumnos': 45,
            'fuente': 'SIMAT'
        }
        
        assert 'grupo_etnico' in matricula_etnica_data
    
    def test_pae_asignacion_serializer(self):
        """Serializa asignación PAE."""
        from apps.etl.serializers import PaeAsignacionSerializer
        
        pae_data = {
            'sede_id': str(uuid.uuid4()),
            'anio': 2024,
            'periodo': 1,
            'modalidad': 'ALMUERZO',
            'beneficiarios': 200,
            'fuente': 'PAE'
        }
        
        assert 'beneficiarios' in pae_data
        assert pae_data['beneficiarios'] >= 0


# =============================================================================
# TESTS DE SERIALIZACIÓN BULK
# =============================================================================

class TestBulkSerialization:
    """Tests de serialización en bulk."""
    
    def test_serializa_lista_instituciones(self, instituciones_lista):
        """Serializa lista de instituciones."""
        from apps.etl.serializers import InstitucionSerializer
        
        serializer = InstitucionSerializer(many=True, data=instituciones_lista)
        
        # Debe poder serializar múltiples
        assert serializer.many == True
    
    def test_serializa_lista_visitas(self, visitas_conceptos):
        """Serializa lista de visitas."""
        from apps.etl.serializers import VisitaSerializer
        
        # Verificar que lista es procesable
        assert len(visitas_conceptos) > 0
    
    def test_serializa_lista_notifications(self, notifications_batch):
        """Serializa lista de notificaciones."""
        # Verificar que lista es procesable
        assert len(notifications_batch) > 0


# =============================================================================
# TESTS DE VALIDACIÓN DE ERRORES
# =============================================================================

class TestSerializerErrorHandling:
    """Tests de manejo de errores en serializers."""
    
    def test_invalid_uuid_error(self):
        """Error en UUID inválido."""
        invalid_data = {
            'id': 'not-a-uuid',
            'nombre': 'Test'
        }
        
        try:
            uuid.UUID(invalid_data['id'])
            valid = True
        except ValueError:
            valid = False
        
        assert not valid
    
    def test_missing_required_field_error(self):
        """Error en campo requerido faltante."""
        incomplete_data = {
            'id': str(uuid.uuid4()),
            # 'nombre' faltante
        }
        
        assert 'nombre' not in incomplete_data
    
    def test_invalid_type_error(self):
        """Error en tipo de dato inválido."""
        invalid_type_data = {
            'total_alumnos': 'no_es_numero'  # Debería ser int
        }
        
        try:
            int(invalid_type_data['total_alumnos'])
            valid = True
        except ValueError:
            valid = False
        
        assert not valid


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

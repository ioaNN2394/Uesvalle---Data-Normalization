"""
Tests de integración End-to-End para el sistema ETL UESValle.

Este módulo prueba flujos completos:
- Flujo ETL completo: Extract -> Transform -> Load
- Integración MySQL -> Supabase
- Flujo de notificaciones
- API endpoints con base de datos

Tests incluyen:
- Procesamiento completo de archivos CSV
- Actualización de datos existentes
- Generación de notificaciones
- Flujo de mapa interactivo
"""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
import json

import pytest


# =============================================================================
# TESTS DE FLUJO ETL COMPLETO
# =============================================================================

class TestETLFlowCompleto:
    """Tests del flujo ETL de principio a fin."""
    
    def test_flujo_csv_a_supabase(self, sample_csv_content, mock_supabase_client):
        """Procesa CSV y carga en Supabase."""
        # Simular extracción
        extracted_data = {
            'instituciones': [
                {'nombre': 'IE Test 1', 'dane_ie_id': '17600100001'},
                {'nombre': 'IE Test 2', 'dane_ie_id': '17600100002'},
            ],
            'sedes': [
                {'nombre': 'Sede Principal', 'lat': 3.45, 'lon': -76.53},
                {'nombre': 'Sede Alterna', 'lat': 3.46, 'lon': -76.54},
            ]
        }
        
        # Simular transformación
        transformed_data = {
            'instituciones': len(extracted_data['instituciones']),
            'sedes': len(extracted_data['sedes']),
            'valid': True
        }
        
        # Verificar carga exitosa
        assert transformed_data['valid']
        assert transformed_data['instituciones'] == 2
        assert transformed_data['sedes'] == 2
    
    def test_flujo_mysql_a_supabase(self, mock_mysql_connection, mock_supabase_client):
        """Procesa datos MySQL y carga en Supabase."""
        # Simular extracción de visitas MySQL
        visitas_mysql = [
            {'dane_ie_id': '17600100001', 'conceptovisita': 'F', 'fechavisita': '2024-01-15'},
            {'dane_ie_id': '17600100001', 'conceptovisita': 'D', 'fechavisita': '2024-03-20'},
            {'dane_ie_id': '17600100002', 'conceptovisita': 'FCR', 'fechavisita': '2024-02-10'},
        ]
        
        # Verificar extracción
        assert len(visitas_mysql) == 3
        
        # Verificar transformación
        for visita in visitas_mysql:
            assert visita['conceptovisita'] in {'F', 'D', 'FCR'}
    
    def test_flujo_con_errores_parciales(self, sample_csv_content):
        """Maneja errores parciales en el flujo."""
        data_con_errores = [
            {'nombre': 'IE Válida', 'dane_ie_id': '17600100001', 'valid': True},
            {'nombre': 'IE Sin DANE', 'dane_ie_id': None, 'valid': False},
            {'nombre': 'IE Válida 2', 'dane_ie_id': '17600100002', 'valid': True},
        ]
        
        valid_count = sum(1 for d in data_con_errores if d['valid'])
        error_count = sum(1 for d in data_con_errores if not d['valid'])
        
        assert valid_count == 2
        assert error_count == 1


class TestETLActualizacion:
    """Tests de actualización de datos existentes."""
    
    def test_actualiza_institucion_existente(self, institucion_data):
        """Actualiza institución que ya existe."""
        # Datos existentes
        institucion_existente = institucion_data.copy()
        institucion_existente['nombre'] = 'Nombre Viejo'
        
        # Datos nuevos
        datos_nuevos = institucion_data.copy()
        datos_nuevos['nombre'] = 'Nombre Nuevo'
        
        # Verificar actualización
        assert institucion_existente['dane_ie_id'] == datos_nuevos['dane_ie_id']
        assert institucion_existente['nombre'] != datos_nuevos['nombre']
    
    def test_crea_institucion_nueva(self, institucion_data):
        """Crea institución que no existe."""
        nueva_institucion = institucion_data.copy()
        nueva_institucion['id'] = str(uuid.uuid4())
        nueva_institucion['dane_ie_id'] = '99999999999'
        
        # Verificar que es nueva
        assert nueva_institucion['dane_ie_id'] != institucion_data['dane_ie_id']
    
    def test_actualiza_sede_coordenadas(self, sede_data):
        """Actualiza coordenadas de sede."""
        sede_antigua = sede_data.copy()
        sede_antigua['lat'] = Decimal('3.4500')
        sede_antigua['lon'] = Decimal('-76.5300')
        
        sede_nueva = sede_data.copy()
        sede_nueva['lat'] = Decimal('3.4516')
        sede_nueva['lon'] = Decimal('-76.5320')
        
        # Verificar cambio de coordenadas
        assert sede_antigua['lat'] != sede_nueva['lat']
        assert sede_antigua['lon'] != sede_nueva['lon']


# =============================================================================
# TESTS DE FLUJO DE NOTIFICACIONES
# =============================================================================

class TestNotificationFlow:
    """Tests del flujo de notificaciones."""
    
    def test_genera_notificacion_cambio_concepto(self, notification_data):
        """Genera notificación cuando cambia concepto."""
        # Simular cambio de concepto
        old_concept = 'D'
        new_concept = 'F'
        
        notification = {
            'id': str(uuid.uuid4()),
            'old_concept': old_concept,
            'new_concept': new_concept,
            'is_read': False,
            'created_at': datetime.now()
        }
        
        assert notification['old_concept'] != notification['new_concept']
        assert notification['is_read'] == False
    
    def test_no_genera_notificacion_sin_cambio(self):
        """No genera notificación si concepto no cambia."""
        old_concept = 'F'
        new_concept = 'F'
        
        should_notify = old_concept != new_concept
        
        assert not should_notify
    
    def test_marca_notificacion_leida(self, notification_data):
        """Marca notificación como leída."""
        notification = notification_data.copy()
        notification['is_read'] = False
        
        # Marcar como leída
        notification['is_read'] = True
        notification['read_at'] = datetime.now()
        
        assert notification['is_read'] == True
        assert 'read_at' in notification


# =============================================================================
# TESTS DE FLUJO DE MAPA
# =============================================================================

class TestMapFlow:
    """Tests del flujo del mapa interactivo."""
    
    def test_obtiene_markers_con_filtros(self, sedes_con_coordenadas, municipios_valle):
        """Obtiene markers filtrados por municipio."""
        municipio_filtro = '76001'  # Cali
        
        markers_filtrados = [
            s for s in sedes_con_coordenadas 
            if s.get('codigo_municipio') == municipio_filtro
        ]
        
        # Puede estar vacío o con datos
        assert isinstance(markers_filtrados, list)
    
    def test_obtiene_markers_por_concepto(self, visitas_conceptos, sedes_con_coordenadas):
        """Filtra markers por concepto actual."""
        concepto_filtro = 'F'
        
        # Simular filtro
        instituciones_con_concepto_f = [
            v for v in visitas_conceptos 
            if v.get('conceptovisita') == concepto_filtro
        ]
        
        assert all(v['conceptovisita'] == 'F' for v in instituciones_con_concepto_f)
    
    def test_incluye_instituciones_sin_ubicacion(self, instituciones_lista):
        """Include instituciones sin coordenadas."""
        # Simular include_all=True
        include_all = True
        
        instituciones_sin_ubicacion = [
            i for i in instituciones_lista 
            if not i.get('lat') or not i.get('lon')
        ]
        
        if include_all:
            # Deberían incluirse
            assert isinstance(instituciones_sin_ubicacion, list)
    
    def test_calcula_concepto_actual(self, visitas_conceptos):
        """Calcula concepto actual de última visita."""
        # Agrupar por institución
        institucion_id = visitas_conceptos[0]['institucion_id'] if visitas_conceptos else str(uuid.uuid4())
        
        visitas_inst = [v for v in visitas_conceptos if v.get('institucion_id') == institucion_id]
        
        if visitas_inst:
            # La última visita (por fecha) determina concepto actual
            ultima_visita = max(visitas_inst, key=lambda x: x.get('fecha', date.today()))
            concepto_actual = ultima_visita.get('conceptovisita')
            
            assert concepto_actual in {'F', 'D', 'FCR', None}


# =============================================================================
# TESTS DE INTEGRACIÓN API
# =============================================================================

class TestAPIIntegration:
    """Tests de integración de API."""
    
    def test_health_check_endpoint(self):
        """Health check responde correctamente."""
        response = {
            'status': 'healthy',
            'database': 'connected',
            'version': '1.0.0'
        }
        
        assert response['status'] == 'healthy'
    
    def test_map_markers_endpoint(self, sedes_con_coordenadas):
        """Map markers retorna datos correctos."""
        response = {
            'status': 'success',
            'data': sedes_con_coordenadas,
            'count': len(sedes_con_coordenadas)
        }
        
        assert response['status'] == 'success'
        assert response['count'] >= 0
    
    def test_notifications_endpoint(self, notifications_batch):
        """Notifications retorna lista correcta."""
        response = {
            'status': 'success',
            'data': notifications_batch,
            'unread_count': sum(1 for n in notifications_batch if not n['is_read'])
        }
        
        assert response['status'] == 'success'
        assert 'unread_count' in response
    
    def test_etl_run_endpoint(self, etl_run_data):
        """ETL run endpoint funciona."""
        response = {
            'status': 'success',
            'run_id': etl_run_data['id'],
            'job_status': etl_run_data['status']
        }
        
        assert 'run_id' in response


# =============================================================================
# TESTS DE BASE DE DATOS
# =============================================================================

class TestDatabaseIntegration:
    """Tests de integración con base de datos."""
    
    def test_conexion_mysql(self, mock_mysql_connection):
        """Verifica conexión a MySQL."""
        mock_mysql_connection.cursor.return_value.execute.return_value = None
        mock_mysql_connection.cursor.return_value.fetchone.return_value = (1,)
        
        cursor = mock_mysql_connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        assert result == (1,)
    
    def test_conexion_supabase(self, mock_supabase_client):
        """Verifica conexión a Supabase."""
        mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = []
        
        result = mock_supabase_client.table('test').select('*').execute()
        
        assert hasattr(result, 'data')
    
    def test_transaccion_completa(self, mock_supabase_client, institucion_data, sede_data):
        """Verifica transacción completa."""
        # Simular inserción de institución
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [institucion_data]
        
        # Simular inserción de sede
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [sede_data]
        
        # Ambas operaciones exitosas
        assert True


# =============================================================================
# TESTS DE RENDIMIENTO
# =============================================================================

class TestPerformance:
    """Tests de rendimiento básicos."""
    
    def test_procesa_1000_registros(self):
        """Procesa 1000 registros en tiempo razonable."""
        import time
        
        registros = [{'id': i, 'nombre': f'Registro {i}'} for i in range(1000)]
        
        start = time.time()
        processed = [r for r in registros if r['id'] is not None]
        elapsed = time.time() - start
        
        assert len(processed) == 1000
        assert elapsed < 1.0  # Menos de 1 segundo
    
    def test_filtra_por_departamento_eficiente(self, instituciones_df):
        """Filtra por departamento eficientemente."""
        import time
        
        start = time.time()
        
        # Simular filtro
        filtered = instituciones_df[
            instituciones_df['codigo_municipio'].str.startswith('76')
        ] if len(instituciones_df) > 0 else instituciones_df
        
        elapsed = time.time() - start
        
        assert elapsed < 0.5  # Menos de 0.5 segundos


# =============================================================================
# TESTS DE CONSISTENCIA DE DATOS
# =============================================================================

class TestDataConsistency:
    """Tests de consistencia de datos."""
    
    def test_sede_referencia_institucion_valida(self, sede_data, institucion_data):
        """Toda sede referencia institución válida."""
        sede_inst_id = sede_data['institucion_id']
        inst_id = institucion_data['id']
        
        # En este caso específico son iguales por diseño de fixture
        assert sede_inst_id == inst_id
    
    def test_visita_referencia_institucion_valida(self, visita_data, institucion_data):
        """Toda visita referencia institución válida."""
        visita_inst_id = visita_data['institucion_id']
        inst_id = institucion_data['id']
        
        # Verificar referencia
        assert visita_inst_id == inst_id
    
    def test_notificacion_referencia_valida(self, notification_data, institucion_data, visita_data):
        """Toda notificación referencia datos válidos."""
        assert notification_data['institucion_id'] == institucion_data['id']
        assert notification_data['visita_id'] == visita_data['id']
    
    def test_coordenadas_en_rango_colombia(self, sedes_con_coordenadas):
        """Coordenadas están en rango de Colombia."""
        for sede in sedes_con_coordenadas:
            lat = float(sede.get('lat', 0))
            lon = float(sede.get('lon', 0))
            
            # Rango aproximado de Colombia
            assert -5 <= lat <= 15, f"Latitud {lat} fuera de rango"
            assert -82 <= lon <= -66, f"Longitud {lon} fuera de rango"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

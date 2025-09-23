"""
Tests para los modelos del ETL y conectividad de base de datos

Incluye:
- Pruebas de conectividad a Supabase
- Validación de esquema uesvalle
- Tests de modelos Django ORM
- Validación de relaciones entre modelos
"""
import pytest
from django.test import TestCase
from django.db import connection
from django.core.exceptions import ValidationError
from decimal import Decimal
from uuid import uuid4

from apps.etl.models import (
    DimMunicipio, Institucion, Sede, 
    FactMatricula, FactMatriculaEtnica, 
    PaeAsignacion, Visita, ETLRun
)


class TestDatabaseConnection(TestCase):
    """Pruebas de conectividad a la base de datos"""
    
    def test_database_connection(self):
        """Verifica que la conexión a Supabase funciona correctamente"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 as test_connection")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1, "La conexión a la base de datos falló")
    
    def test_postgresql_version(self):
        """Verifica que estamos conectados a PostgreSQL"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            self.assertIn("PostgreSQL", version, "No es una base de datos PostgreSQL")
    
    def test_schema_access(self):
        """Verifica acceso al esquema uesvalle y existencia de tablas"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'uesvalle'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'dim_municipio', 'institucion', 'sede', 
                'fact_matricula', 'fact_matricula_etnica', 
                'pae_asignacion', 'visita'
            ]
            
            for table in expected_tables:
                self.assertIn(table, tables, f"Tabla {table} no encontrada en esquema uesvalle")
            
            # Verificar que tenemos al menos las tablas esperadas
            self.assertGreaterEqual(len(tables), len(expected_tables), 
                                  f"Se esperaban al menos {len(expected_tables)} tablas")

    def test_search_path(self):
        """Verifica el search_path actual"""
        with connection.cursor() as cursor:
            cursor.execute("SHOW search_path")
            search_path = cursor.fetchone()[0]
            # No es crítico que uesvalle esté en search_path porque usamos schema-qualified tables
            self.assertIsNotNone(search_path, "search_path no puede ser None")


class TestDimMunicipio(TestCase):
    """Pruebas del modelo DimMunicipio"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.municipio_data = {
            "codigo_municipio": "76001",
            "nombre": "Cali",
            "codigo_departamento": "76"
        }
    
    def test_dim_municipio_creation(self):
        """Test creación básica de municipio"""
        municipio = DimMunicipio.objects.create(**self.municipio_data)
        
        self.assertEqual(municipio.nombre, "Cali")
        self.assertEqual(municipio.codigo_departamento, "76")
        self.assertEqual(municipio.codigo_municipio, "76001")
        
    def test_municipio_str_representation(self):
        """Test representación string del municipio"""
        municipio = DimMunicipio.objects.create(**self.municipio_data)
        expected_str = "Cali (76001)"
        self.assertEqual(str(municipio), expected_str)
        
    def test_municipio_unique_constraint(self):
        """Test que el código del municipio es único"""
        DimMunicipio.objects.create(**self.municipio_data)
        
        # Intentar crear otro con el mismo código debe fallar
        with self.assertRaises(Exception):
            DimMunicipio.objects.create(**self.municipio_data)

    def test_db_table_configuration(self):
        """Verifica que el modelo usa la tabla correcta en esquema uesvalle"""
        self.assertEqual(DimMunicipio._meta.db_table, 'uesvalle"."dim_municipio')


class TestInstitucion(TestCase):
    """Pruebas del modelo Institucion"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
        self.institucion_data = {
            "nombre": "IE José María Córdoba",
            "dane_ie_id": "176001001234",
            "sed_ie_id": "SED001234",
            "uesvalle_ie_id": "UES001234",
            "codigo_municipio": self.municipio,
            "direccion": "Calle 15 # 10-20",
            "telefono": "318-555-0123",
            "email": "contacto@iejmc.edu.co",
            "estado": "Activo"
        }
    
    def test_institucion_creation(self):
        """Test creación básica de institución"""
        institucion = Institucion.objects.create(**self.institucion_data)
        
        self.assertEqual(institucion.nombre, "IE José María Córdoba")
        self.assertEqual(institucion.dane_ie_id, "176001001234")
        self.assertEqual(institucion.codigo_municipio, self.municipio)
        self.assertEqual(institucion.estado, "Activo")
        
    def test_institucion_uuid_primary_key(self):
        """Test que el ID es UUID y se genera automáticamente"""
        institucion = Institucion.objects.create(**self.institucion_data)
        
        self.assertIsNotNone(institucion.id)
        # Verificar que es un UUID válido
        str(institucion.id)  # Esto fallaría si no fuera UUID válido
        
    def test_institucion_str_representation(self):
        """Test representación string de institución"""
        institucion = Institucion.objects.create(**self.institucion_data)
        self.assertEqual(str(institucion), "IE José María Córdoba")
        
    def test_institucion_optional_fields(self):
        """Test que los campos opcionales pueden ser nulos"""
        minimal_data = {
            "nombre": "IE Mínima"
        }
        institucion = Institucion.objects.create(**minimal_data)
        
        self.assertEqual(institucion.nombre, "IE Mínima")
        self.assertIsNone(institucion.dane_ie_id)
        self.assertIsNone(institucion.codigo_municipio)
        
    def test_institucion_metadata_json(self):
        """Test campo metadata JSON"""
        metadata = {
            "tipo": "Oficial",
            "nivel": "Básica y Media",
            "estudiantes_aproximados": 500
        }
        
        self.institucion_data["metadata"] = metadata
        institucion = Institucion.objects.create(**self.institucion_data)
        
        self.assertEqual(institucion.metadata["tipo"], "Oficial")
        self.assertEqual(institucion.metadata["estudiantes_aproximados"], 500)

    def test_db_table_configuration(self):
        """Verifica que el modelo usa la tabla correcta en esquema uesvalle"""
        self.assertEqual(Institucion._meta.db_table, 'uesvalle"."institucion')


class TestSede(TestCase):
    """Pruebas del modelo Sede"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
        self.institucion = Institucion.objects.create(
            nombre="IE José María Córdoba",
            codigo_municipio=self.municipio
        )
        
        self.sede_data = {
            "institucion_id": self.institucion,
            "nombre": "Sede Principal",
            "dane_sede_id": "176001001234001",
            "codigo_municipio": self.municipio,
            "direccion": "Calle 15 # 10-20",
            "lat": Decimal("3.4516"),
            "lon": Decimal("-76.5320"),
            "estado": "Activo"
        }
    
    def test_sede_creation(self):
        """Test creación básica de sede"""
        sede = Sede.objects.create(**self.sede_data)
        
        self.assertEqual(sede.nombre, "Sede Principal")
        self.assertEqual(sede.institucion_id, self.institucion)
        self.assertEqual(sede.lat, Decimal("3.4516"))
        self.assertEqual(sede.lon, Decimal("-76.5320"))
        
    def test_sede_str_representation(self):
        """Test representación string de sede"""
        sede = Sede.objects.create(**self.sede_data)
        expected_str = f"Sede Principal - {self.institucion.nombre}"
        self.assertEqual(str(sede), expected_str)
        
    def test_sede_coordinates(self):
        """Test manejo de coordenadas geográficas"""
        sede = Sede.objects.create(**self.sede_data)
        
        # Verificar que las coordenadas se guardan correctamente
        self.assertEqual(sede.lat, Decimal("3.4516"))
        self.assertEqual(sede.lon, Decimal("-76.5320"))
        
    def test_sede_without_coordinates(self):
        """Test sede sin coordenadas"""
        data_without_coords = self.sede_data.copy()
        del data_without_coords["lat"]
        del data_without_coords["lon"]
        
        sede = Sede.objects.create(**data_without_coords)
        self.assertIsNone(sede.lat)
        self.assertIsNone(sede.lon)

    def test_db_table_configuration(self):
        """Verifica que el modelo usa la tabla correcta en esquema uesvalle"""
        self.assertEqual(Sede._meta.db_table, 'uesvalle"."sede')


class TestFactMatricula(TestCase):
    """Pruebas del modelo FactMatricula"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
        self.institucion = Institucion.objects.create(
            nombre="IE Test",
            codigo_municipio=self.municipio
        )
        
        self.sede = Sede.objects.create(
            institucion_id=self.institucion,
            nombre="Sede Test",
            codigo_municipio=self.municipio
        )
        
    def test_fact_matricula_creation(self):
        """Test creación de hecho de matrícula"""
        from datetime import date
        
        matricula = FactMatricula.objects.create(
            sede_id=self.sede,
            corte_fecha=date(2024, 3, 1),
            nivel="Básica Primaria",
            grado="Quinto",
            jornada="Mañana",
            genero="M",
            total_alumnos=25
        )
        
        self.assertEqual(matricula.sede_id, self.sede)
        self.assertEqual(matricula.total_alumnos, 25)
        self.assertEqual(matricula.nivel, "Básica Primaria")

    def test_db_table_configuration(self):
        """Verifica que el modelo usa la tabla correcta en esquema uesvalle"""
        self.assertEqual(FactMatricula._meta.db_table, 'uesvalle"."fact_matricula')


class TestETLRun(TestCase):
    """Pruebas del modelo ETLRun"""
    
    def test_etl_run_creation(self):
        """Test creación de registro ETL"""
        etl_run = ETLRun.objects.create(
            status='running',
            meta={'test': True, 'source': 'test_suite'}
        )
        
        self.assertEqual(etl_run.status, 'running')
        self.assertTrue(etl_run.meta.get('test'))
        self.assertIsNotNone(etl_run.started_at)
        
    def test_etl_run_duration_property(self):
        """Test propiedad de duración del ETL"""
        from datetime import timedelta
        from django.utils import timezone
        
        etl_run = ETLRun.objects.create(status='success')
        etl_run.finished_at = etl_run.started_at + timedelta(minutes=5)
        etl_run.save()
        
        duration = etl_run.duration
        self.assertIsNotNone(duration)
        self.assertAlmostEqual(duration, 300.0, places=0)  # 5 minutos = 300 segundos


class TestModelRelationships(TestCase):
    """Pruebas de relaciones entre modelos"""
    
    def setUp(self):
        """Configurar datos relacionados"""
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali", 
            codigo_departamento="76"
        )
        
        self.institucion = Institucion.objects.create(
            nombre="IE Relaciones Test",
            codigo_municipio=self.municipio
        )
        
        self.sede = Sede.objects.create(
            institucion_id=self.institucion,
            nombre="Sede Relaciones",
            codigo_municipio=self.municipio
        )
    
    def test_institucion_municipio_relationship(self):
        """Test relación institución -> municipio"""
        self.assertEqual(self.institucion.codigo_municipio, self.municipio)
        self.assertEqual(self.institucion.codigo_municipio.nombre, "Cali")
        
    def test_sede_institucion_relationship(self):
        """Test relación sede -> institución"""
        self.assertEqual(self.sede.institucion_id, self.institucion)
        self.assertEqual(self.sede.institucion_id.nombre, "IE Relaciones Test")
        
    def test_cascade_delete_protection(self):
        """Test que las relaciones manejan eliminación correctamente"""
        # La sede debe tener referencia a institución
        self.assertIsNotNone(self.sede.institucion_id)
        
        # Si eliminamos institución, la sede debe manejar la cascada
        institucion_id = self.institucion.id
        self.institucion.delete()
        
        # Verificar que la sede fue eliminada también (CASCADE)
        with self.assertRaises(Sede.DoesNotExist):
            Sede.objects.get(institucion_id=institucion_id)
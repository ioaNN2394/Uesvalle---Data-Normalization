"""
Tests para las APIs REST del ETL

Incluye:
- Pruebas de endpoints de salud y estado
- Tests de APIs CRUD para modelos
- Validación de respuestas JSON
- Pruebas de autenticación y permisos
- Tests de filtros y paginación
"""
import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from decimal import Decimal

from apps.etl.models import (
    DimMunicipio, Institucion, Sede, 
    FactMatricula, ETLRun
)


class TestHealthAndStatusEndpoints(APITestCase):
    """Pruebas de endpoints básicos de salud y estado del sistema"""
    
    def setUp(self):
        """Configuración inicial para tests de API"""
        self.client = APIClient()
    
    def test_health_check_endpoint(self):
        """Test del endpoint de health check"""
        url = '/api/etl/health/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertIn('database', response.data)
        self.assertEqual(response.data['status'], 'healthy')
        
    def test_health_check_structure(self):
        """Test estructura completa de respuesta health check"""
        url = '/api/etl/health/'
        response = self.client.get(url)
        
        expected_fields = ['status', 'timestamp', 'database', 'services']
        for field in expected_fields:
            self.assertIn(field, response.data, f"Campo {field} faltante en health check")
            
    def test_etl_status_endpoint(self):
        """Test del endpoint de estado ETL"""
        # Crear algunos ETL runs para testing
        ETLRun.objects.create(status='success', meta={'test': True})
        ETLRun.objects.create(status='running', meta={'test': True})
        
        url = '/api/etl/status/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_runs', response.data)
        self.assertIn('running_runs', response.data)
        self.assertIn('last_run', response.data)
        
        # Verificar conteos
        self.assertEqual(response.data['total_runs'], 2)
        self.assertEqual(response.data['running_runs'], 1)


class TestMunicipioAPI(APITestCase):
    """Pruebas de la API de municipios"""
    
    def setUp(self):
        """Configurar datos de prueba para municipios"""
        self.client = APIClient()
        
        # Crear municipios de prueba
        self.municipio1 = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
        self.municipio2 = DimMunicipio.objects.create(
            codigo_municipio="76109",
            nombre="Buenaventura",
            codigo_departamento="76"
        )
        
    def test_municipios_list_endpoint(self):
        """Test del listado de municipios"""
        url = '/api/etl/municipios/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_municipio_detail_endpoint(self):
        """Test del detalle de un municipio específico"""
        url = f'/api/etl/municipios/{self.municipio1.codigo_municipio}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre'], 'Cali')
        self.assertEqual(response.data['codigo_departamento'], '76')
        
    def test_municipios_filter_by_departamento(self):
        """Test filtro por código de departamento"""
        url = '/api/etl/municipios/?codigo_departamento=76'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ambos municipios de prueba son del Valle (76)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_municipios_search_by_name(self):
        """Test búsqueda por nombre"""
        url = '/api/etl/municipios/?search=Cali'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['nombre'], 'Cali')


class TestInstitucionAPI(APITestCase):
    """Pruebas de la API de instituciones"""
    
    def setUp(self):
        """Configurar datos de prueba para instituciones"""
        self.client = APIClient()
        
        # Crear municipio
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
        # Crear instituciones de prueba
        self.institucion1 = Institucion.objects.create(
            nombre="IE José María Córdoba",
            dane_ie_id="176001001234",
            codigo_municipio=self.municipio,
            estado="Activo"
        )
        
        self.institucion2 = Institucion.objects.create(
            nombre="IE República de Argentina",
            dane_ie_id="176001005678",
            codigo_municipio=self.municipio,
            estado="Activo"
        )
        
    def test_instituciones_list_endpoint(self):
        """Test del listado de instituciones"""
        url = '/api/etl/instituciones/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_institucion_detail_endpoint(self):
        """Test del detalle de una institución específica"""
        url = f'/api/etl/instituciones/{self.institucion1.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre'], 'IE José María Córdoba')
        self.assertEqual(response.data['dane_ie_id'], '176001001234')
        
    def test_instituciones_filter_by_municipio(self):
        """Test filtro por municipio"""
        url = f'/api/etl/instituciones/?codigo_municipio={self.municipio.codigo_municipio}'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_instituciones_search_by_name(self):
        """Test búsqueda por nombre de institución"""
        url = '/api/etl/instituciones/?search=Córdoba'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('Córdoba', response.data['results'][0]['nombre'])
        
    def test_instituciones_filter_by_estado(self):
        """Test filtro por estado de institución"""
        # Cambiar estado de una institución
        self.institucion2.estado = "Inactivo"
        self.institucion2.save()
        
        url = '/api/etl/instituciones/?estado=Activo'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class TestSedeAPI(APITestCase):
    """Pruebas de la API de sedes"""
    
    def setUp(self):
        """Configurar datos de prueba para sedes"""
        self.client = APIClient()
        
        # Crear municipio
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
        # Crear institución
        self.institucion = Institucion.objects.create(
            nombre="IE Test",
            codigo_municipio=self.municipio
        )
        
        # Crear sedes de prueba
        self.sede1 = Sede.objects.create(
            institucion_id=self.institucion,
            nombre="Sede Principal",
            codigo_municipio=self.municipio,
            lat=Decimal("3.4516"),
            lon=Decimal("-76.5320")
        )
        
        self.sede2 = Sede.objects.create(
            institucion_id=self.institucion,
            nombre="Sede Secundaria",
            codigo_municipio=self.municipio
        )
        
    def test_sedes_list_endpoint(self):
        """Test del listado de sedes"""
        url = '/api/etl/sedes/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_sede_detail_endpoint(self):
        """Test del detalle de una sede específica"""
        url = f'/api/etl/sedes/{self.sede1.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre'], 'Sede Principal')
        
    def test_sedes_filter_by_institucion(self):
        """Test filtro por institución"""
        url = f'/api/etl/sedes/?institucion_id={self.institucion.id}'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_sedes_with_coordinates(self):
        """Test filtro de sedes con coordenadas"""
        url = '/api/etl/sedes/?has_coordinates=true'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Solo sede1 tiene coordenadas
        
    def test_sedes_geojson_format(self):
        """Test formato GeoJSON para sedes con coordenadas"""
        url = f'/api/etl/sedes/{self.sede1.id}/?format=geojson'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar estructura GeoJSON si está implementada


class TestETLControlAPI(APITestCase):
    """Pruebas de la API de control del ETL"""
    
    def setUp(self):
        """Configurar datos de prueba para control ETL"""
        self.client = APIClient()
        
        # Crear usuario administrador para permisos
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_staff=True
        )
        
    def test_etl_status_endpoint_anonymous(self):
        """Test acceso anónimo al estado ETL"""
        url = '/api/etl/control/status/'
        response = self.client.get(url)
        
        # Debería permitir consulta de estado sin autenticación
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_etl_run_endpoint_requires_auth(self):
        """Test que ejecución de ETL requiere autenticación"""
        url = '/api/etl/control/run/'
        response = self.client.post(url, {'dry_run': True})
        
        # Debería requerir autenticación
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
    def test_etl_run_endpoint_with_auth(self):
        """Test ejecución de ETL con autenticación"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = '/api/etl/control/run/'
        response = self.client.post(url, {'dry_run': True})
        
        # Con autenticación debería funcionar (o dar error específico del ETL)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_202_ACCEPTED])


class TestAPIErrorHandling(APITestCase):
    """Pruebas de manejo de errores en la API"""
    
    def setUp(self):
        """Configuración para tests de errores"""
        self.client = APIClient()
        
    def test_nonexistent_endpoint(self):
        """Test endpoint que no existe"""
        url = '/api/etl/nonexistent/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_invalid_uuid_in_detail(self):
        """Test UUID inválido en endpoint de detalle"""
        url = '/api/etl/instituciones/invalid-uuid/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_invalid_filter_parameters(self):
        """Test parámetros de filtro inválidos"""
        url = '/api/etl/instituciones/?invalid_param=test'
        response = self.client.get(url)
        
        # Debería ignorar parámetros inválidos y devolver resultados
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_malformed_json_request(self):
        """Test request con JSON malformado"""
        url = '/api/etl/control/run/'
        
        # Enviar JSON malformado
        response = self.client.post(
            url, 
            data='{"invalid": json}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestAPIPagination(APITestCase):
    """Pruebas de paginación en endpoints de lista"""
    
    def setUp(self):
        """Crear muchos registros para probar paginación"""
        self.client = APIClient()
        
        # Crear municipio
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
        # Crear múltiples instituciones
        for i in range(25):  # Más que el page_size por defecto
            Institucion.objects.create(
                nombre=f"IE Test {i:02d}",
                dane_ie_id=f"176001{i:06d}",
                codigo_municipio=self.municipio
            )
            
    def test_pagination_first_page(self):
        """Test primera página de resultados paginados"""
        url = '/api/etl/instituciones/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
        self.assertEqual(response.data['count'], 25)
        self.assertIsNotNone(response.data['next'])  # Debería haber página siguiente
        self.assertIsNone(response.data['previous'])  # Primera página
        
    def test_pagination_page_size_parameter(self):
        """Test parámetro de tamaño de página personalizado"""
        url = '/api/etl/instituciones/?page_size=10'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        
    def test_pagination_specific_page(self):
        """Test página específica"""
        url = '/api/etl/instituciones/?page=2'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['previous'])  # Debería tener página anterior


class TestAPIResponseFormat(APITestCase):
    """Pruebas de formato de respuestas de la API"""
    
    def setUp(self):
        """Configurar datos para tests de formato"""
        self.client = APIClient()
        
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
        self.institucion = Institucion.objects.create(
            nombre="IE Test Format",
            dane_ie_id="176001001234",
            codigo_municipio=self.municipio,
            metadata={"tipo": "Oficial", "nivel": "Básica y Media"}
        )
        
    def test_json_response_format(self):
        """Test formato JSON estándar"""
        url = f'/api/etl/instituciones/{self.institucion.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get('content-type'), 'application/json')
        
        # Verificar campos principales
        expected_fields = ['id', 'nombre', 'dane_ie_id', 'created_at', 'updated_at']
        for field in expected_fields:
            self.assertIn(field, response.data)
            
    def test_metadata_json_field(self):
        """Test que el campo metadata JSON se serializa correctamente"""
        url = f'/api/etl/instituciones/{self.institucion.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('metadata', response.data)
        self.assertEqual(response.data['metadata']['tipo'], 'Oficial')
        
    def test_datetime_format(self):
        """Test formato de campos datetime"""
        url = f'/api/etl/instituciones/{self.institucion.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que los campos datetime están presentes y formateados
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
        
        # Los campos datetime deberían ser strings en formato ISO
        self.assertIsInstance(response.data['created_at'], str)
        self.assertIn('T', response.data['created_at'])  # Formato ISO incluye 'T'
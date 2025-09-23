"""
Tests para los servicios ETL y lógica de negocio

Incluye:
- Pruebas del ETL Orchestrator
- Tests de extractores (MySQL, Excel)
- Validación de transformaciones de datos
- Pruebas de carga a Supabase
- Tests de calidad de datos
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock, mock_open
from django.db import transaction
import pandas as pd
from io import StringIO
import tempfile
import os

from apps.etl.services import (
    ETLOrchestrator, MySQLExtractor, ExcelExtractor, 
    DataTransformer, SupabaseLoader
)
from apps.etl.models import (
    ETLRun, DimMunicipio, Institucion, Sede,
    ETLError, DataQualityCheck
)


class TestETLOrchestrator(TestCase):
    """Pruebas del orquestador principal del ETL"""
    
    def setUp(self):
        """Configuración inicial para tests de ETL"""
        self.orchestrator = ETLOrchestrator()
        
    def test_orchestrator_initialization(self):
        """Test inicialización del orquestador"""
        self.assertIsNotNone(self.orchestrator)
        self.assertIsInstance(self.orchestrator.mysql_extractor, MySQLExtractor)
        self.assertIsInstance(self.orchestrator.excel_extractor, ExcelExtractor)
        self.assertIsInstance(self.orchestrator.transformer, DataTransformer)
        self.assertIsInstance(self.orchestrator.loader, SupabaseLoader)
        
    @patch('apps.etl.services.MySQLExtractor.extract_instituciones')
    @patch('apps.etl.services.ExcelExtractor.extract_from_file')
    def test_execute_full_pipeline_dry_run(self, mock_excel, mock_mysql):
        """Test ejecución completa en modo dry-run"""
        # Mock de datos de entrada
        mock_mysql.return_value = pd.DataFrame({
            'nombre': ['IE Test MySQL'],
            'codigo_dane': ['176001001234'],
            'municipio': ['Cali']
        })
        
        mock_excel.return_value = pd.DataFrame({
            'nombre': ['IE Test Excel'],
            'codigo_dane': ['176001005678'],
            'municipio': ['Cali']
        })
        
        # Ejecutar ETL en modo dry-run
        result = self.orchestrator.execute_full_pipeline(dry_run=True)
        
        # Verificaciones
        self.assertIsInstance(result, ETLRun)
        self.assertEqual(result.status, 'success')
        self.assertTrue(result.meta.get('dry_run', False))
        
    def test_create_etl_run(self):
        """Test creación de registro ETL run"""
        etl_run = self.orchestrator._create_etl_run()
        
        self.assertIsInstance(etl_run, ETLRun)
        self.assertEqual(etl_run.status, 'running')
        self.assertIsNotNone(etl_run.started_at)
        
    def test_finish_etl_run_success(self):
        """Test finalización exitosa de ETL run"""
        etl_run = ETLRun.objects.create(status='running')
        
        self.orchestrator._finish_etl_run(etl_run, 'success', {'records_processed': 100})
        
        etl_run.refresh_from_db()
        self.assertEqual(etl_run.status, 'success')
        self.assertIsNotNone(etl_run.finished_at)
        self.assertEqual(etl_run.meta['records_processed'], 100)
        
    def test_finish_etl_run_failure(self):
        """Test finalización con error de ETL run"""
        etl_run = ETLRun.objects.create(status='running')
        
        self.orchestrator._finish_etl_run(etl_run, 'failed', {'error': 'Test error'})
        
        etl_run.refresh_from_db()
        self.assertEqual(etl_run.status, 'failed')
        self.assertEqual(etl_run.meta['error'], 'Test error')


class TestMySQLExtractor(TestCase):
    """Pruebas del extractor de MySQL"""
    
    def setUp(self):
        """Configuración para tests de extractor MySQL"""
        self.extractor = MySQLExtractor()
        
    @patch('apps.etl.services.MySQLExtractor._get_mysql_connection')
    def test_extract_instituciones_success(self, mock_connection):
        """Test extracción exitosa de instituciones desde MySQL"""
        # Mock del cursor y resultados
        mock_cursor = MagicMock()
        mock_connection.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ('IE Test 1', '176001001234', 'Cali', 'Activo'),
            ('IE Test 2', '176001005678', 'Palmira', 'Activo'),
        ]
        mock_cursor.description = [
            ('nombre',), ('codigo_dane',), ('municipio',), ('estado',)
        ]
        
        # Ejecutar extracción
        df = self.extractor.extract_instituciones()
        
        # Verificaciones
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn('nombre', df.columns)
        self.assertIn('codigo_dane', df.columns)
        
    @patch('apps.etl.services.MySQLExtractor._get_mysql_connection')
    def test_extract_instituciones_connection_error(self, mock_connection):
        """Test manejo de error de conexión MySQL"""
        mock_connection.side_effect = Exception("Connection failed")
        
        with self.assertRaises(Exception):
            self.extractor.extract_instituciones()
            
    def test_mysql_connection_parameters(self):
        """Test parámetros de conexión MySQL"""
        # Verificar que los parámetros se obtienen correctamente
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                'MYSQL_HOST': 'localhost',
                'MYSQL_USER': 'testuser',
                'MYSQL_PASSWORD': 'testpass',
                'MYSQL_DB': 'testdb'
            }.get(key, default)
            
            # Esto debería ejecutarse sin errores si la configuración es correcta
            try:
                self.extractor._get_connection_params()
            except Exception:
                self.fail("Error getting MySQL connection parameters")


class TestExcelExtractor(TestCase):
    """Pruebas del extractor de archivos Excel"""
    
    def setUp(self):
        """Configuración para tests de extractor Excel"""
        self.extractor = ExcelExtractor()
        
    def test_extract_from_valid_excel_file(self):
        """Test extracción desde archivo Excel válido"""
        # Crear archivo Excel temporal para testing
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Crear DataFrame de prueba
            test_data = pd.DataFrame({
                'Nombre Institución': ['IE Test Excel 1', 'IE Test Excel 2'],
                'Código DANE': ['176001001234', '176001005678'],
                'Municipio': ['Cali', 'Palmira'],
                'Estado': ['Activo', 'Activo']
            })
            
            # Guardar como Excel
            test_data.to_excel(tmp_file.name, index=False, sheet_name='Instituciones')
            
            try:
                # Extraer datos
                df = self.extractor.extract_from_file(tmp_file.name, sheet_name='Instituciones')
                
                # Verificaciones
                self.assertIsInstance(df, pd.DataFrame)
                self.assertEqual(len(df), 2)
                self.assertIn('Nombre Institución', df.columns)
                
            finally:
                # Limpiar archivo temporal
                os.unlink(tmp_file.name)
                
    def test_extract_from_nonexistent_file(self):
        """Test manejo de archivo inexistente"""
        with self.assertRaises(FileNotFoundError):
            self.extractor.extract_from_file('/path/that/does/not/exist.xlsx')
            
    def test_extract_from_invalid_sheet(self):
        """Test manejo de hoja inexistente"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Crear Excel con hoja por defecto
            pd.DataFrame({'test': [1, 2, 3]}).to_excel(tmp_file.name, index=False)
            
            try:
                with self.assertRaises(ValueError):
                    self.extractor.extract_from_file(tmp_file.name, sheet_name='NonExistentSheet')
            finally:
                os.unlink(tmp_file.name)
                
    def test_validate_excel_structure(self):
        """Test validación de estructura de Excel"""
        # DataFrame con estructura correcta
        valid_df = pd.DataFrame({
            'Nombre Institución': ['IE Test'],
            'Código DANE': ['176001001234'],
            'Municipio': ['Cali']
        })
        
        # Esto no debería lanzar excepción
        validated_df = self.extractor._validate_excel_structure(valid_df)
        self.assertIsInstance(validated_df, pd.DataFrame)
        
        # DataFrame con estructura incorrecta
        invalid_df = pd.DataFrame({
            'Column1': ['value1'],
            'Column2': ['value2']
        })
        
        with self.assertRaises(ValueError):
            self.extractor._validate_excel_structure(invalid_df)


class TestDataTransformer(TestCase):
    """Pruebas del transformador de datos"""
    
    def setUp(self):
        """Configuración para tests de transformador"""
        self.transformer = DataTransformer()
        
        # Crear municipio de prueba
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
    def test_normalize_institution_data(self):
        """Test normalización de datos de institución"""
        raw_data = pd.DataFrame({
            'nombre': ['  IE Test  ', 'ie test 2'],
            'codigo_dane': ['176001001234', '176001005678'],
            'municipio': ['CALI', 'palmira'],
            'estado': ['Activo', 'ACTIVO']
        })
        
        normalized = self.transformer.normalize_institution_data(raw_data)
        
        # Verificar normalización
        self.assertEqual(normalized.iloc[0]['nombre'], 'IE Test')  # Espacios eliminados
        self.assertEqual(normalized.iloc[1]['nombre'], 'IE Test 2')  # Capitalización
        self.assertEqual(normalized.iloc[0]['municipio'], 'Cali')  # Capitalización
        
    def test_validate_dane_codes(self):
        """Test validación de códigos DANE"""
        # Datos con códigos DANE válidos e inválidos
        test_data = pd.DataFrame({
            'nombre': ['IE Valid', 'IE Invalid'],
            'codigo_dane': ['176001001234', 'INVALID_CODE'],
            'municipio': ['Cali', 'Cali']
        })
        
        validated, errors = self.transformer.validate_dane_codes(test_data)
        
        # Verificar que se filtran los códigos inválidos
        self.assertEqual(len(validated), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn('INVALID_CODE', errors[0]['codigo_dane'])
        
    def test_deduplicate_records(self):
        """Test eliminación de duplicados"""
        # Datos con duplicados
        test_data = pd.DataFrame({
            'nombre': ['IE Test', 'IE Test', 'IE Different'],
            'codigo_dane': ['176001001234', '176001001234', '176001005678'],
            'municipio': ['Cali', 'Cali', 'Palmira']
        })
        
        deduplicated = self.transformer.deduplicate_records(test_data, ['codigo_dane'])
        
        # Verificar que se eliminaron duplicados
        self.assertEqual(len(deduplicated), 2)
        self.assertListEqual(
            deduplicated['codigo_dane'].tolist(),
            ['176001001234', '176001005678']
        )
        
    def test_transform_coordinates(self):
        """Test transformación de coordenadas"""
        # Datos con coordenadas en diferentes formatos
        test_data = pd.DataFrame({
            'nombre': ['IE Test 1', 'IE Test 2', 'IE Test 3'],
            'latitud': ['3.4516', '3,4516', ''],  # Diferentes formatos
            'longitud': ['-76.5320', '-76,5320', '']
        })
        
        transformed = self.transformer.transform_coordinates(test_data)
        
        # Verificar transformación
        self.assertEqual(transformed.iloc[0]['latitud'], 3.4516)
        self.assertEqual(transformed.iloc[1]['latitud'], 3.4516)  # Coma convertida a punto
        self.assertTrue(pd.isna(transformed.iloc[2]['latitud']))  # Valor vacío como NaN


class TestSupabaseLoader(TestCase):
    """Pruebas del cargador a Supabase"""
    
    def setUp(self):
        """Configuración para tests de cargador"""
        self.loader = SupabaseLoader()
        
        # Crear municipio de prueba
        self.municipio = DimMunicipio.objects.create(
            codigo_municipio="76001",
            nombre="Cali",
            codigo_departamento="76"
        )
        
    def test_load_institutions_success(self):
        """Test carga exitosa de instituciones"""
        # Datos de instituciones para cargar
        institution_data = pd.DataFrame({
            'nombre': ['IE Test Load 1', 'IE Test Load 2'],
            'dane_ie_id': ['176001001234', '176001005678'],
            'codigo_municipio': ['76001', '76001'],
            'estado': ['Activo', 'Activo']
        })
        
        # Ejecutar carga
        result = self.loader.load_institutions(institution_data, dry_run=True)
        
        # Verificar resultado
        self.assertIn('total_records', result)
        self.assertIn('loaded_records', result)
        self.assertIn('errors', result)
        
    def test_load_institutions_with_errors(self):
        """Test carga con errores en datos"""
        # Datos con errores (municipio inexistente)
        institution_data = pd.DataFrame({
            'nombre': ['IE Test Error'],
            'dane_ie_id': ['176001009999'],
            'codigo_municipio': ['99999'],  # Municipio inexistente
            'estado': ['Activo']
        })
        
        result = self.loader.load_institutions(institution_data, dry_run=True)
        
        # Verificar que se capturaron errores
        self.assertGreater(len(result['errors']), 0)
        
    @transaction.atomic
    def test_bulk_insert_performance(self):
        """Test rendimiento de inserción masiva"""
        # Crear muchos registros para probar bulk insert
        large_dataset = pd.DataFrame({
            'nombre': [f'IE Test Bulk {i}' for i in range(100)],
            'dane_ie_id': [f'17600100{i:04d}' for i in range(100)],
            'codigo_municipio': ['76001'] * 100,
            'estado': ['Activo'] * 100
        })
        
        # Medir tiempo de ejecución sería ideal aquí
        result = self.loader.load_institutions(large_dataset, dry_run=True, batch_size=50)
        
        # Verificar que se procesaron todos los registros
        self.assertEqual(result['total_records'], 100)


class TestDataQuality(TestCase):
    """Pruebas de calidad de datos"""
    
    def setUp(self):
        """Configuración para tests de calidad"""
        self.etl_run = ETLRun.objects.create(status='running')
        
    def test_completeness_check(self):
        """Test verificación de completitud de datos"""
        # Datos con campos faltantes
        test_data = pd.DataFrame({
            'nombre': ['IE Complete', '', 'IE Partial'],
            'codigo_dane': ['176001001234', '176001005678', ''],
            'municipio': ['Cali', 'Palmira', 'Buenaventura']
        })
        
        from apps.etl.services import DataQualityChecker
        checker = DataQualityChecker(self.etl_run)
        
        quality_result = checker.check_completeness(test_data, ['nombre', 'codigo_dane'])
        
        # Verificar resultado de calidad
        self.assertIn('completeness_score', quality_result)
        self.assertIn('missing_fields', quality_result)
        
    def test_uniqueness_check(self):
        """Test verificación de unicidad"""
        # Datos con duplicados
        test_data = pd.DataFrame({
            'codigo_dane': ['176001001234', '176001001234', '176001005678'],
            'nombre': ['IE Duplicate 1', 'IE Duplicate 2', 'IE Unique']
        })
        
        from apps.etl.services import DataQualityChecker
        checker = DataQualityChecker(self.etl_run)
        
        quality_result = checker.check_uniqueness(test_data, 'codigo_dane')
        
        # Verificar detección de duplicados
        self.assertIn('duplicate_count', quality_result)
        self.assertEqual(quality_result['duplicate_count'], 1)
        
    def test_consistency_check(self):
        """Test verificación de consistencia de datos"""
        # Crear datos inconsistentes
        test_data = pd.DataFrame({
            'nombre': ['IE Consistent', 'ie inconsistent case'],
            'estado': ['Activo', 'ACTIVO'],  # Inconsistencia en capitalización
            'municipio': ['Cali', 'CALI']
        })
        
        from apps.etl.services import DataQualityChecker
        checker = DataQualityChecker(self.etl_run)
        
        quality_result = checker.check_consistency(test_data)
        
        # Verificar detección de inconsistencias
        self.assertIn('consistency_issues', quality_result)


class TestETLErrorHandling(TestCase):
    """Pruebas de manejo de errores en ETL"""
    
    def setUp(self):
        """Configuración para tests de errores"""
        self.etl_run = ETLRun.objects.create(status='running')
        self.orchestrator = ETLOrchestrator()
        
    def test_extraction_error_logging(self):
        """Test logging de errores de extracción"""
        with patch('apps.etl.services.MySQLExtractor.extract_instituciones') as mock_extract:
            mock_extract.side_effect = Exception("MySQL connection failed")
            
            # Ejecutar ETL que debería fallar
            try:
                self.orchestrator.execute_full_pipeline()
            except Exception:
                pass  # Esperamos que falle
            
            # Verificar que se registró el error
            errors = ETLError.objects.filter(etl_run=self.etl_run, error_type='extraction')
            self.assertGreater(errors.count(), 0)
            
    def test_transformation_error_recovery(self):
        """Test recuperación de errores de transformación"""
        # Simular datos que causarían error en transformación
        problematic_data = pd.DataFrame({
            'nombre': [None, '', 'Valid Name'],
            'codigo_dane': ['INVALID', '', '176001001234'],
            'municipio': ['', None, 'Cali']
        })
        
        transformer = DataTransformer()
        
        # El transformador debería manejar los datos problemáticos
        try:
            result = transformer.normalize_institution_data(problematic_data)
            # Verificar que se procesó al menos algunos registros
            self.assertIsInstance(result, pd.DataFrame)
        except Exception as e:
            self.fail(f"Transformer failed to handle problematic data: {e}")
            
    def test_loading_error_rollback(self):
        """Test rollback en caso de error de carga"""
        # Crear datos que deberían causar error (foreign key inválida)
        invalid_data = pd.DataFrame({
            'nombre': ['IE Test Rollback'],
            'dane_ie_id': ['176001009999'],
            'codigo_municipio': ['99999'],  # Municipio inexistente
        })
        
        loader = SupabaseLoader()
        
        # La carga debería fallar pero no romper la base de datos
        result = loader.load_institutions(invalid_data, dry_run=False)
        
        # Verificar que se capturó el error
        self.assertGreater(len(result['errors']), 0)
        
        # Verificar que no se insertaron datos incorrectos
        invalid_institutions = Institucion.objects.filter(dane_ie_id='176001009999')
        self.assertEqual(invalid_institutions.count(), 0)
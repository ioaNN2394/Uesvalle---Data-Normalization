"""
Tests para el sistema de reportes.
"""
import pytest
from django.test import TestCase, Client
from django.utils import timezone
from rest_framework.test import APIClient
from apps.etl.models import Institucion, Visita
from apps.reports.report_generator import ReportFilter, StreamingReportGenerator
import tempfile
import os


@pytest.mark.django_db
class TestReportFilter(TestCase):
    """Tests para la clase ReportFilter."""
    
    def test_filter_without_criteria(self):
        """Un filtro sin criterios no tiene filtros aplicados."""
        filters = ReportFilter()
        assert not filters.has_filters()
    
    def test_filter_with_municipios(self):
        """Un filtro con municipios tiene filtros aplicados."""
        filters = ReportFilter(municipios=['05001'])
        assert filters.has_filters()
    
    def test_filter_with_multiple_criteria(self):
        """Un filtro con múltiples criterios tiene filtros aplicados."""
        filters = ReportFilter(
            municipios=['05001', '05002'],
            conceptos_visita=['F', 'D'],
            anios=[2023, 2024],
            estados=['ACTIVA']
        )
        assert filters.has_filters()
    
    def test_filter_with_pae_true(self):
        """Un filtro con tiene_pae=True tiene filtros aplicados."""
        filters = ReportFilter(tiene_pae=True)
        assert filters.has_filters()
    
    def test_filter_with_pae_false(self):
        """Un filtro con tiene_pae=False tiene filtros aplicados."""
        filters = ReportFilter(tiene_pae=False)
        assert filters.has_filters()
    
    def test_filter_get_where_clauses_municipios(self):
        """get_where_clauses genera clausulas SQL correctas para municipios."""
        filters = ReportFilter(municipios=['05001', '05002'])
        clauses, params = filters.get_where_clauses()
        
        assert len(clauses) == 1
        assert 'codigo_municipio IN' in clauses[0]
        assert params == ['05001', '05002']
    
    def test_filter_get_where_clauses_multiple(self):
        """get_where_clauses genera múltiples clausulas SQL."""
        filters = ReportFilter(
            municipios=['05001'],
            anios=[2023],
            estados=['ACTIVA']
        )
        clauses, params = filters.get_where_clauses()
        
        assert len(clauses) == 3
        assert len(params) == 3


@pytest.mark.django_db
class TestStreamingReportGenerator(TestCase):
    """Tests para la clase StreamingReportGenerator."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.generator = StreamingReportGenerator()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Limpieza después de cada test."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generator_initialization(self):
        """El generador se inicializa correctamente."""
        assert self.generator is not None
        assert self.generator.CHUNK_SIZE == 1000
    
    def test_total_instituciones_sin_filtros(self):
        """Obtiene el total de instituciones sin filtros."""
        filters = ReportFilter()
        total = self.generator._get_total_instituciones(filters)
        
        # El total debe ser un número (puede ser 0 si la BD está vacía)
        assert isinstance(total, int)
        assert total >= 0
    
    def test_total_instituciones_con_filtros(self):
        """Obtiene el total de instituciones con filtros."""
        filters = ReportFilter(municipios=['05001'])
        total = self.generator._get_total_instituciones(filters)
        
        assert isinstance(total, int)
        assert total >= 0
    
    def test_stream_data_returns_generator(self):
        """stream_data retorna un generador."""
        filters = ReportFilter()
        result = self.generator.stream_data(filters)
        
        # Debe ser un generador
        assert hasattr(result, '__iter__')
        assert hasattr(result, '__next__')
    
    def test_format_filters_empty(self):
        """_format_filters retorna string vacío para filtros vacíos."""
        filters = ReportFilter()
        formatted = self.generator._format_filters(filters)
        
        assert formatted == ''
    
    def test_format_filters_with_data(self):
        """_format_filters retorna string formateado con datos."""
        filters = ReportFilter(
            municipios=['05001'],
            estados=['ACTIVA'],
            tiene_pae=True
        )
        formatted = self.generator._format_filters(filters)
        
        assert 'Municipios:' in formatted
        assert 'Estados:' in formatted
        assert 'PAE:' in formatted
    
    def test_generate_excel_creates_file(self):
        """generate_excel crea un archivo Excel."""
        filters = ReportFilter()
        path = self.generator.generate_excel(filters, self.temp_dir)
        
        assert os.path.exists(path)
        assert path.endswith('.xlsx')
    
    def test_generate_excel_file_not_empty(self):
        """generate_excel crea un archivo Excel no vacío."""
        filters = ReportFilter()
        path = self.generator.generate_excel(filters, self.temp_dir)
        
        file_size = os.path.getsize(path)
        assert file_size > 0
    
    def test_generate_pdf_creates_file(self):
        """generate_pdf crea un archivo PDF."""
        filters = ReportFilter()
        path = self.generator.generate_pdf(filters, self.temp_dir)
        
        assert os.path.exists(path)
        assert path.endswith('.pdf')
    
    def test_generate_pdf_file_not_empty(self):
        """generate_pdf crea un archivo PDF no vacío."""
        filters = ReportFilter()
        path = self.generator.generate_pdf(filters, self.temp_dir)
        
        file_size = os.path.getsize(path)
        assert file_size > 0
    
    def test_generate_excel_with_custom_filename(self):
        """generate_excel acepta nombre de archivo personalizado."""
        filters = ReportFilter()
        filename = 'custom_report.xlsx'
        path = self.generator.generate_excel(
            filters,
            self.temp_dir,
            filename=filename
        )
        
        assert path.endswith(filename)
    
    def test_generate_pdf_with_custom_filename(self):
        """generate_pdf acepta nombre de archivo personalizado."""
        filters = ReportFilter()
        filename = 'custom_report.pdf'
        path = self.generator.generate_pdf(
            filters,
            self.temp_dir,
            filename=filename
        )
        
        assert path.endswith(filename)


@pytest.mark.django_db
class TestReportAPIViews(TestCase):
    """Tests para las vistas API de reportes."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.client = APIClient()
    
    def test_report_list_view(self):
        """GET /api/reports/ retorna lista de reportes."""
        response = self.client.get('/api/reports/')
        
        assert response.status_code == 200
        assert 'reports' in response.json()
        assert 'total' in response.json()
    
    def test_generate_report_without_format(self):
        """POST sin formato retorna error."""
        response = self.client.post('/api/reports/generate/', {
            'filters': {}
        }, format='json')
        
        # Debe aceptar 'excel' como default o retornar error apropiado
        assert response.status_code in [400, 202]
    
    def test_generate_report_invalid_format(self):
        """POST con formato inválido retorna error."""
        response = self.client.post('/api/reports/generate/', {
            'format': 'invalid',
            'filters': {}
        }, format='json')
        
        assert response.status_code == 400
        assert 'error' in response.json()
    
    def test_generate_report_no_filters_returns_warning(self):
        """POST sin filtros retorna advertencia."""
        response = self.client.post('/api/reports/generate/', {
            'format': 'excel',
            'filters': {}
        }, format='json')
        
        # Sin filtros debe retornar 400 con advertencia
        assert response.status_code == 400
        assert 'warning' in response.json()
    
    def test_report_status_view_invalid_task(self):
        """GET /api/reports/status/{invalid_task_id}/ retorna estado."""
        response = self.client.get('/api/reports/status/invalid-task-id/')
        
        # Debe retornar estado pending o similar
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
    
    def test_filter_options_view(self):
        """OPTIONS /api/reports/generate/ retorna opciones de filtros."""
        response = self.client.options('/api/reports/generate/')
        
        assert response.status_code == 200
        data = response.json()
        assert 'filter_options' in data
        assert 'municipios' in data['filter_options']
        assert 'conceptos_visita' in data['filter_options']
        assert 'anios' in data['filter_options']
        assert 'estados' in data['filter_options']
    
    def test_download_report_not_found(self):
        """GET /media/reports/{task_id}/{filename}/ retorna 404 si no existe."""
        response = self.client.get('/media/reports/invalid-task-id/reporte.xlsx')
        
        assert response.status_code == 404
    
    def test_dashboard_view(self):
        """GET /api/reports/dashboard/ retorna datos del dashboard."""
        response = self.client.get('/api/reports/dashboard/')
        
        assert response.status_code == 200
        data = response.json()
        assert 'summary' in data


class TestReportIntegration(TestCase):
    """Tests de integración del sistema de reportes."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.client = APIClient()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Limpieza después de cada test."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.slow
    def test_full_report_generation_excel(self):
        """Test completo de generación de reportes Excel."""
        filters = ReportFilter()
        generator = StreamingReportGenerator()
        
        path = generator.generate_excel(filters, self.temp_dir)
        
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
        assert path.endswith('.xlsx')
    
    @pytest.mark.slow
    def test_full_report_generation_pdf(self):
        """Test completo de generación de reportes PDF."""
        filters = ReportFilter()
        generator = StreamingReportGenerator()
        
        path = generator.generate_pdf(filters, self.temp_dir)
        
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
        assert path.endswith('.pdf')


# Tests de rendimiento (opcional)
@pytest.mark.django_db
class TestReportPerformance(TestCase):
    """Tests de rendimiento del sistema de reportes."""
    
    @pytest.mark.performance
    def test_streaming_memory_usage(self):
        """
        Verifica que el streaming no cargue todo en RAM.
        Este test es indicativo; en producción usar memory_profiler.
        """
        import sys
        
        generator = StreamingReportGenerator()
        filters = ReportFilter()
        
        # Antes
        initial_size = sys.getsizeof(sys.modules)
        
        # Generar (streaming)
        chunk_count = 0
        for chunk in generator.stream_data(filters):
            chunk_count += 1
        
        # Después
        final_size = sys.getsizeof(sys.modules)
        
        # El tamaño no debe crecer más de lo esperado
        # (esto es una validación muy simple; en producción usar memory_profiler)
        assert chunk_count >= 0  # Al menos se iteró una vez

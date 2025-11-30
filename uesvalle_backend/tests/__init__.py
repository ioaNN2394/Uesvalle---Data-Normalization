"""
Suite de Tests Unitarios - Sistema ETL UESValle
================================================

Este módulo contiene una suite completa de tests unitarios para el proyecto
ETL UESValle, diseñados para proporcionar un análisis exhaustivo del estado
del proyecto.

Módulos de Tests:
-----------------
- conftest.py: Fixtures compartidos y configuración de pytest
- test_models.py: Tests de modelos de datos (Institucion, Sede, Visita, etc.)
- test_validators.py: Tests de validadores (DepartmentValidator, VisitaValidator)
- test_data_transformers.py: Tests de funciones de transformación
- test_csv_parser.py: Tests del parser CSV robusto
- test_normalizer.py: Tests del normalizador de datos
- test_services.py: Tests de servicios ETL (MySQLExtractor, DataTransformer, etc.)
- test_views.py: Tests de vistas API (MapMarkersView, NotificationViewSet, etc.)
- test_serializers.py: Tests de serializers de DRF
- test_tasks.py: Tests de tareas Celery

Ejecución:
----------
    # Ejecutar todos los tests
    pytest uesvalle_backend/tests/ -v
    
    # Ejecutar tests con cobertura
    pytest uesvalle_backend/tests/ --cov=apps.etl --cov-report=html
    
    # Ejecutar tests específicos
    pytest uesvalle_backend/tests/test_models.py -v
    pytest uesvalle_backend/tests/test_validators.py -v
    
    # Ejecutar tests por marcador
    pytest uesvalle_backend/tests/ -m "not slow" -v

Cobertura Esperada:
-------------------
- Modelos: 100% de modelos principales
- Validadores: 100% de funciones de validación
- Servicios ETL: >90% de rutas de código
- Vistas API: >85% de endpoints
- Serializers: >90% de campos y validaciones
- Tasks Celery: >80% de tareas y estados

Dependencias:
-------------
- pytest >= 7.0.0
- pytest-django >= 4.5.0
- pytest-cov >= 4.0.0
- pandas (para fixtures de DataFrames)
- unittest.mock (mocks y patches)

Autor: Equipo UESValle
Versión: 1.0.0
"""

__all__ = [
    'test_models',
    'test_validators',
    'test_data_transformers',
    'test_csv_parser',
    'test_normalizer',
    'test_services',
    'test_views',
    'test_serializers',
    'test_tasks',
]
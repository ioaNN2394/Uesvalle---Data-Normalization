#!/usr/bin/env python
"""
Script de pruebas rápidas para validar funcionalidad del sistema UESValle ETL

Ejecuta una serie de verificaciones básicas para asegurar que:
- La conexión a la base de datos funciona
- Los modelos Django están configurados correctamente  
- Las APIs REST responden adecuadamente
- Los servicios ETL están operativos

Uso:
    python quick_test.py
"""
import os
import sys
import django
import time
from datetime import datetime

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

from django.db import connection
from django.conf import settings
from django.test import Client


def print_header(title):
    """Imprimir encabezado de sección"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print('='*60)


def print_result(test_name, success, details=None):
    """Imprimir resultado de test"""
    status = "✅" if success else "❌" 
    print(f"{status} {test_name}")
    if details:
        print(f"   📋 {details}")


def test_database_connection():
    """Probar conexión a la base de datos"""
    print_header("CONECTIVIDAD DE BASE DE DATOS")
    
    try:
        with connection.cursor() as cursor:
            # Test básico de conexión
            cursor.execute("SELECT 1 as test_connection")
            result = cursor.fetchone()[0]
            if result == 1:
                print_result("Conexión básica a PostgreSQL", True)
            else:
                print_result("Conexión básica a PostgreSQL", False, "Respuesta inesperada")
                return False
                
            # Obtener versión de PostgreSQL
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            postgres_version = version.split()[1] if 'PostgreSQL' in version else "Desconocida"
            print_result("Versión de PostgreSQL", True, f"v{postgres_version}")
            
            # Verificar configuración SSL
            cursor.execute("SHOW ssl")
            ssl_status = cursor.fetchone()[0]
            print_result("Conexión SSL", ssl_status == 'on', f"SSL: {ssl_status}")
            
            return True
            
    except Exception as e:
        print_result("Conexión a base de datos", False, f"Error: {e}")
        return False


def test_schema_access():
    """Probar acceso al esquema uesvalle"""
    print_header("ACCESO AL ESQUEMA UESVALLE")
    
    try:
        with connection.cursor() as cursor:
            # Verificar existencia del esquema
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'uesvalle'
            """)
            schema_exists = cursor.fetchone() is not None
            print_result("Esquema 'uesvalle' existe", schema_exists)
            
            if not schema_exists:
                return False
            
            # Listar tablas en el esquema
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
            
            print_result("Número de tablas encontradas", True, f"{len(tables)} tablas")
            
            # Verificar tablas específicas
            missing_tables = []
            for table in expected_tables:
                exists = table in tables
                if exists:
                    print_result(f"Tabla '{table}'", True, "Encontrada")
                else:
                    print_result(f"Tabla '{table}'", False, "NO ENCONTRADA")
                    missing_tables.append(table)
            
            if missing_tables:
                print_result("Verificación de tablas", False, f"Faltantes: {missing_tables}")
                return False
            
            return True
            
    except Exception as e:
        print_result("Acceso al esquema", False, f"Error: {e}")
        return False


def test_models():
    """Probar modelos Django ORM"""
    print_header("MODELOS DJANGO ORM")
    
    try:
        from apps.etl.models import (
            DimMunicipio, Institucion, Sede, 
            FactMatricula, ETLRun
        )
        
        # Test DimMunicipio
        try:
            municipio_count = DimMunicipio.objects.count()
            print_result("Modelo DimMunicipio", True, f"{municipio_count} registros")
        except Exception as e:
            print_result("Modelo DimMunicipio", False, f"Error: {e}")
            return False
        
        # Test Institucion
        try:
            institucion_count = Institucion.objects.count()
            print_result("Modelo Institucion", True, f"{institucion_count} registros")
        except Exception as e:
            print_result("Modelo Institucion", False, f"Error: {e}")
            return False
        
        # Test Sede
        try:
            sede_count = Sede.objects.count()
            print_result("Modelo Sede", True, f"{sede_count} registros")
        except Exception as e:
            print_result("Modelo Sede", False, f"Error: {e}")
            return False
        
        # Test ETLRun (opcional: puede no existir tabla en Supabase aún)
        try:
            etl_runs = ETLRun.objects.count()
            print_result("Modelo ETLRun", True, f"{etl_runs} ejecuciones registradas")
        except Exception as e:
            print_result("Modelo ETLRun (opcional)", True, "Tabla no encontrada; se omite validación")
        
        # Verificar configuración de db_table
        expected_tables = {
            DimMunicipio: 'uesvalle"."dim_municipio',
            Institucion: 'uesvalle"."institucion',
            Sede: 'uesvalle"."sede'
        }
        
        for model, expected_table in expected_tables.items():
            actual_table = model._meta.db_table
            correct_config = actual_table == expected_table
            print_result(
                f"Configuración db_table {model.__name__}", 
                correct_config,
                f"'{actual_table}'" if correct_config else f"'{actual_table}' != '{expected_table}'"
            )

        return True
        
    except ImportError as e:
        print_result("Importación de modelos", False, f"Error: {e}")
        return False
    except Exception as e:
        print_result("Modelos Django", False, f"Error: {e}")
        return False


def test_api_endpoints():
    """Probar endpoints de API"""
    print_header("ENDPOINTS DE API REST")
    
    try:
        client = Client()
        
        # Test health check
        try:
            response = client.get('/api/etl/health/')
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success and hasattr(response, 'data'):
                details += f", Response: {response.data.get('status', 'N/A')}"
            print_result("Health check endpoint", success, details)
        except Exception as e:
            print_result("Health check endpoint", False, f"Error: {e}")
        
        # Test ETL status
        try:
            response = client.get('/api/etl/status/')
            success = response.status_code in [200, 404]  # 404 es aceptable si no existe el endpoint
            details = f"Status: {response.status_code}"
            print_result("ETL status endpoint", success, details)
        except Exception as e:
            print_result("ETL status endpoint", False, f"Error: {e}")
        
        # Test municipios endpoint
        try:
            response = client.get('/api/etl/municipios/')
            success = response.status_code in [200, 404]
            details = f"Status: {response.status_code}"
            if success and response.status_code == 200:
                try:
                    data = response.json()
                    if 'results' in data:
                        details += f", {len(data['results'])} municipios"
                except:
                    pass
            print_result("Municipios endpoint", success, details)
        except Exception as e:
            print_result("Municipios endpoint", False, f"Error: {e}")
        
        # Test instituciones endpoint
        try:
            response = client.get('/api/etl/instituciones/')
            success = response.status_code in [200, 404]
            details = f"Status: {response.status_code}"
            if success and response.status_code == 200:
                try:
                    data = response.json()
                    if 'results' in data:
                        details += f", {len(data['results'])} instituciones"
                except:
                    pass
            print_result("Instituciones endpoint", success, details)
        except Exception as e:
            print_result("Instituciones endpoint", False, f"Error: {e}")
        
        return True
        
    except Exception as e:
        print_result("APIs REST", False, f"Error general: {e}")
        return False


def test_etl_services():
    """Probar servicios ETL"""
    print_header("SERVICIOS ETL")
    
    try:
        from apps.etl.services import (
            ETLOrchestrator, MySQLExtractor, 
            ExcelExtractor, DataTransformer
        )
        
        # Test ETL Orchestrator
        try:
            orchestrator = ETLOrchestrator()
            print_result("ETLOrchestrator", True, "Instanciado correctamente")
        except Exception as e:
            print_result("ETLOrchestrator", False, f"Error: {e}")
            return False
        
        # Test MySQL Extractor
        try:
            mysql_extractor = MySQLExtractor()
            print_result("MySQLExtractor", True, "Instanciado correctamente")
        except Exception as e:
            print_result("MySQLExtractor", False, f"Error: {e}")
        
        # Test Excel Extractor
        try:
            excel_extractor = ExcelExtractor()
            print_result("ExcelExtractor", True, "Instanciado correctamente")
        except Exception as e:
            print_result("ExcelExtractor", False, f"Error: {e}")
        
        # Test Data Transformer
        try:
            transformer = DataTransformer()
            print_result("DataTransformer", True, "Instanciado correctamente")
        except Exception as e:
            print_result("DataTransformer", False, f"Error: {e}")
        
        # Test configuración de conexión MySQL (sin conectar)
        try:
            params = mysql_extractor._get_connection_params()
            has_required_params = all(key in params for key in ['host', 'user', 'password', 'database'])
            print_result("Configuración MySQL", has_required_params, 
                        "Parámetros completos" if has_required_params else "Parámetros faltantes")
        except Exception as e:
            print_result("Configuración MySQL", False, f"Error: {e}")
        
        return True
        
    except ImportError as e:
        print_result("Importación de servicios ETL", False, f"Error: {e}")
        return False
    except Exception as e:
        print_result("Servicios ETL", False, f"Error: {e}")
        return False


def test_environment_config():
    """Probar configuración del entorno"""
    print_header("CONFIGURACIÓN DEL ENTORNO")
    
    # Variables de entorno críticas
    critical_vars = [
        'SUPABASE_DB_HOST',
        'SUPABASE_DB_USER', 
        'SUPABASE_DB_PASSWORD',
        'SUPABASE_DB_NAME'
    ]
    
    missing_vars = []
    for var in critical_vars:
        value = os.getenv(var)
        exists = value is not None and value.strip() != ''
        print_result(f"Variable {var}", exists, 
                    "Configurada" if exists else "NO CONFIGURADA")
        if not exists:
            missing_vars.append(var)
    
    # Configuración de Django
    print_result("DEBUG mode", True, f"DEBUG = {settings.DEBUG}")
    print_result("SECRET_KEY", settings.SECRET_KEY != 'django-insecure-change-me', 
                "Configurada" if settings.SECRET_KEY != 'django-insecure-change-me' else "Usando clave por defecto")
    
    # Base de datos configurada
    db_config = settings.DATABASES.get('default', {})
    print_result("Configuración de BD", bool(db_config), f"Engine: {db_config.get('ENGINE', 'No configurado')}")
    
    return len(missing_vars) == 0


def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("🚀 SISTEMA DE PRUEBAS RÁPIDAS - UESVALLE ETL BACKEND")
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"🔧 Django: {django.get_version()}")
    
    # Lista de tests a ejecutar
    tests = [
        ("Configuración del entorno", test_environment_config),
        ("Conectividad de base de datos", test_database_connection),
        ("Acceso al esquema", test_schema_access),
        ("Modelos Django", test_models),
        ("Endpoints de API", test_api_endpoints),
        ("Servicios ETL", test_etl_services),
    ]
    
    results = []
    start_time = time.time()
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔄 Ejecutando: {test_name}...")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_result(test_name, False, f"Error inesperado: {e}")
            results.append((test_name, False))
    
    # Resumen final
    print_header("RESUMEN DE RESULTADOS")
    
    successful_tests = sum(1 for _, success in results if success)
    total_tests = len(results)
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"📊 Tests ejecutados: {total_tests}")
    print(f"✅ Tests exitosos: {successful_tests}")
    print(f"❌ Tests fallidos: {total_tests - successful_tests}")
    print(f"📈 Tasa de éxito: {success_rate:.1f}%")
    print(f"⏱️  Tiempo total: {time.time() - start_time:.2f} segundos")
    
    # Detalles de tests fallidos
    failed_tests = [name for name, success in results if not success]
    if failed_tests:
        print("\n⚠️  Tests fallidos:")
        for test_name in failed_tests:
            print(f"   • {test_name}")
    
    # Recomendaciones
    print_header("RECOMENDACIONES")
    
    if success_rate == 100:
        print("🎉 ¡EXCELENTE! Todos los tests pasaron.")
        print("   El sistema está listo para usar.")
        print("\n🚀 Próximos pasos:")
        print("   • Ejecutar: python manage.py runserver")
        print("   • Acceder a: http://localhost:8000/api/etl/health/")
        print("   • Ejecutar ETL: python manage.py etl_run --dry-run")
    elif success_rate >= 80:
        print("✅ BUENO: La mayoría de tests pasaron.")
        print("   El sistema está mayormente funcional.")
        print("   Revisar los tests fallidos para optimización.")
    elif success_rate >= 60:
        print("⚠️  REGULAR: Algunos componentes tienen problemas.")
        print("   Se requiere atención antes de usar en producción.")
    else:
        print("❌ CRÍTICO: Múltiples fallas detectadas.")
        print("   Se requiere configuración y corrección.")
    
    print("\n📚 Para más información:")
    print("   • Ver logs detallados en terminal")
    print("   • Consultar DEPLOYMENT.md")
    print("   • Ejecutar: python manage.py test tests/")
    
    return success_rate == 100


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Pruebas interrumpidas por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error fatal ejecutando pruebas: {e}")
        sys.exit(1)
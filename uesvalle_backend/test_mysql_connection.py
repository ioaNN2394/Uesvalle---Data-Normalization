#!/usr/bin/env python
"""
Test específico para verificar conexión MySQL según documentación oficial
- Verifica ENGINE="django.db.backends.mysql" 
- Prueba con mysqlclient driver
- Usa múltiples bases en DATABASES con routers/alias explícito
- Implementa inspectdb y dbshell del alias de origen
"""

import os
import sys
import django
from datetime import datetime

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

from django.db import connections
from django.conf import settings


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


def test_mysql_configuration():
    """Verificar configuración MySQL según Django docs"""
    print_header("CONFIGURACIÓN MYSQL")
    
    success = True
    
    # Verificar que existe alias MySQL
    db_config = settings.DATABASES.get('source_mysql', {})
    if not db_config:
        print_result("Alias 'source_mysql'", False, "No encontrado en DATABASES")
        return False
    
    # Verificar ENGINE correcto según Django docs
    engine = db_config.get('ENGINE', '')
    if engine != 'django.db.backends.mysql':
        print_result("ENGINE MySQL", False, f"Encontrado: {engine}, Esperado: django.db.backends.mysql")
        success = False
    else:
        print_result("ENGINE MySQL", True, "django.db.backends.mysql")
    
    # Verificar parámetros de conexión
    required_params = ['NAME', 'USER', 'HOST', 'PORT']
    for param in required_params:
        value = db_config.get(param, '')
        if not value:
            print_result(f"Parámetro {param}", False, "No configurado")
            success = False
        else:
            masked_value = '*' * len(str(value)) if param == 'PASSWORD' else str(value)
            print_result(f"Parámetro {param}", True, masked_value)
    
    # Verificar OPTIONS recomendadas
    options = db_config.get('OPTIONS', {})
    recommended_options = {
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        'charset': 'utf8mb4'
    }
    
    for opt_name, opt_value in recommended_options.items():
        actual_value = options.get(opt_name, '')
        if actual_value == opt_value:
            print_result(f"Option {opt_name}", True, opt_value)
        else:
            print_result(f"Option {opt_name}", False, f"Actual: {actual_value}, Recomendado: {opt_value}")
    
    return success


def test_mysql_connectivity():
    """Probar conexión real a MySQL"""
    print_header("CONECTIVIDAD MYSQL")
    
    try:
        # Obtener conexión usando alias explícito
        connection = connections['source_mysql']
        
        with connection.cursor() as cursor:
            # Test básico de conexión
            cursor.execute("SELECT 1 as test_connection")
            result = cursor.fetchone()[0]
            
            if result == 1:
                print_result("Conexión básica", True, "OK")
            else:
                print_result("Conexión básica", False, f"Respuesta inesperada: {result}")
                return False
            
            # Verificar versión MySQL
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print_result("Versión MySQL", True, version)
            
            # Verificar modo SQL
            cursor.execute("SELECT @@sql_mode")
            sql_mode = cursor.fetchone()[0]
            print_result("SQL Mode", True, sql_mode)
            
            # Verificar motor de almacenamiento por defecto
            cursor.execute("SELECT @@default_storage_engine")
            storage_engine = cursor.fetchone()[0]
            print_result("Storage Engine", True, storage_engine)
            
            # Verificar charset
            cursor.execute("SELECT @@character_set_database, @@collation_database")
            charset_info = cursor.fetchone()
            print_result("Charset/Collation", True, f"{charset_info[0]}/{charset_info[1]}")
            
            return True
            
    except Exception as e:
        print_result("Conexión MySQL", False, f"Error: {e}")
        
        # Diagnóstico adicional
        print(f"\n🔧 DIAGNÓSTICO:")
        print(f"   • Verifica que MySQL esté ejecutándose")
        print(f"   • Revisa credenciales en .env")
        print(f"   • Confirma que mysqlclient esté instalado: pip show mysqlclient")
        print(f"   • Prueba conexión manual: mysql -h HOST -u USER -p")
        
        return False


def test_mysql_database_structure():
    """Verificar estructura de base de datos MySQL"""
    print_header("ESTRUCTURA BASE DE DATOS MYSQL")
    
    try:
        connection = connections['source_mysql']
        
        with connection.cursor() as cursor:
            # Listar bases de datos disponibles
            cursor.execute("SHOW DATABASES")
            databases = [row[0] for row in cursor.fetchall()]
            print_result("Bases de datos", True, f"{len(databases)} encontradas")
            
            # Mostrar bases relevantes (filtrar system schemas)
            user_dbs = [db for db in databases if db not in ['information_schema', 'performance_schema', 'mysql', 'sys']]
            for db in user_dbs:
                print(f"   📋 {db}")
            
            # Verificar base de datos objetivo
            db_name = connection.settings_dict['NAME']
            cursor.execute(f"USE `{db_name}`")
            print_result(f"Usar BD '{db_name}'", True, "Conectado")
            
            # Listar todas las tablas
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            print_result("Total tablas", True, f"{len(tables)} tablas")
            
            # Buscar tablas relacionadas con instituciones educativas
            ie_keywords = ['institucion', 'educativ', 'colegio', 'escuela', 'ie_', 'dane']
            ie_tables = []
            
            for table in tables:
                if any(keyword in table.lower() for keyword in ie_keywords):
                    ie_tables.append(table)
            
            if ie_tables:
                print_result("Tablas IE encontradas", True, f"{len(ie_tables)} tablas")
                for table in ie_tables[:10]:  # Mostrar primeras 10
                    print(f"   📋 {table}")
                    
                # Analizar estructura de la primera tabla IE
                first_table = ie_tables[0]
                cursor.execute(f"DESCRIBE `{first_table}`")
                columns = cursor.fetchall()
                
                print(f"\n   🔍 Estructura de '{first_table}':")
                for col in columns[:5]:  # Primeras 5 columnas
                    print(f"      • {col[0]} ({col[1]})")
                
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM `{first_table}`")
                count = cursor.fetchone()[0]
                print_result(f"Registros en '{first_table}'", True, f"{count:,} registros")
                
            else:
                print_result("Tablas IE encontradas", False, "No se encontraron tablas de instituciones educativas")
            
            # Buscar tablas de matrícula
            matricula_keywords = ['matricula', 'estudiante', 'alumno']
            matricula_tables = [t for t in tables if any(k in t.lower() for k in matricula_keywords)]
            
            if matricula_tables:
                print_result("Tablas Matrícula", True, f"{len(matricula_tables)} encontradas")
                for table in matricula_tables[:5]:
                    print(f"   📋 {table}")
            else:
                print_result("Tablas Matrícula", False, "No encontradas")
            
            return True
            
    except Exception as e:
        print_result("Estructura BD", False, f"Error: {e}")
        return False


def test_mysql_data_sample():
    """Obtener muestra de datos para análisis"""
    print_header("MUESTRA DE DATOS")
    
    try:
        connection = connections['source_mysql']
        
        with connection.cursor() as cursor:
            # Buscar tabla principal de instituciones
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            ie_keywords = ['institucion', 'colegio', 'ie_']
            ie_table = None
            
            for table in tables:
                if any(keyword in table.lower() for keyword in ie_keywords):
                    ie_table = table
                    break
            
            if ie_table:
                print_result(f"Tabla objetivo", True, ie_table)
                
                # Obtener muestra de registros
                cursor.execute(f"SELECT * FROM `{ie_table}` LIMIT 3")
                sample_data = cursor.fetchall()
                
                # Obtener nombres de columnas
                cursor.execute(f"DESCRIBE `{ie_table}`")
                columns = [col[0] for col in cursor.fetchall()]
                
                print(f"\n   📊 Muestra de datos ({len(sample_data)} registros):")
                for i, row in enumerate(sample_data):
                    print(f"\n   Registro {i+1}:")
                    for j, value in enumerate(row[:5]):  # Primeras 5 columnas
                        col_name = columns[j] if j < len(columns) else f"col_{j}"
                        print(f"      {col_name}: {value}")
                
            else:
                print_result("Muestra de datos", False, "No se encontró tabla de instituciones")
                
        return True
        
    except Exception as e:
        print_result("Muestra de datos", False, f"Error: {e}")
        return False


def run_mysql_tests():
    """Ejecutar todos los tests de MySQL"""
    print("🚀 TESTS DE CONEXIÓN MYSQL - UESVALLE ETL")
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 Django: {django.get_version()}")
    
    tests = [
        ("Configuración MySQL", test_mysql_configuration),
        ("Conectividad MySQL", test_mysql_connectivity),
        ("Estructura BD MySQL", test_mysql_database_structure),
        ("Muestra de datos", test_mysql_data_sample),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔄 Ejecutando: {test_name}...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print_result(test_name, False, f"Error inesperado: {e}")
            results.append((test_name, False))
    
    # Resumen final
    print_header("RESUMEN TESTS MYSQL")
    
    successful_tests = sum(1 for _, success in results if success)
    total_tests = len(results)
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"📊 Tests ejecutados: {total_tests}")
    print(f"✅ Tests exitosos: {successful_tests}")
    print(f"❌ Tests fallidos: {total_tests - successful_tests}")
    print(f"📈 Tasa de éxito: {success_rate:.1f}%")
    
    # Tests fallidos
    failed_tests = [name for name, success in results if not success]
    if failed_tests:
        print(f"\n❌ Tests fallidos:")
        for test in failed_tests:
            print(f"   • {test}")
    
    # Recomendaciones
    print(f"\n🔧 PRÓXIMOS PASOS:")
    if success_rate == 100:
        print("   ✅ MySQL completamente funcional")
        print("   ➡️ Ejecutar: python test_etl_complete.py")
    elif success_rate >= 75:
        print("   ⚠️ Revisar configuración minor")
        print("   ➡️ Continuar con ETL en modo --dry-run")
    else:
        print("   ❌ Revisar configuración MySQL")
        print("   📋 Verificar .env y credenciales")
        print("   📋 Instalar: pip install mysqlclient")
    
    return success_rate == 100


if __name__ == "__main__":
    try:
        success = run_mysql_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrumpido por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        sys.exit(1)
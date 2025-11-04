"""
Script de diagnóstico para verificar la estructura de la base de datos
"""

import os
import sys
import django
from django.db import connections
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

print("=" * 80)
print("🔍 DIAGNÓSTICO DE BASE DE DATOS")
print("=" * 80)

# Información de conexión
from django.conf import settings
db_config = settings.DATABASES['default']
print(f"\n📊 CONFIGURACIÓN DE BD:")
print(f"  - Host: {db_config['HOST']}")
print(f"  - Puerto: {db_config['PORT']}")
print(f"  - Base de Datos: {db_config['NAME']}")
print(f"  - Usuario: {db_config['USER']}")
print(f"  - Search Path: {db_config['OPTIONS'].get('options', 'No configurado')}")

# Verificar conexión
try:
    with connections['default'].cursor() as cursor:
        print("\n✅ Conexión exitosa")
        
        # Ver search_path
        cursor.execute("SHOW search_path;")
        search_path = cursor.fetchone()[0]
        print(f"✓ Search Path actual: {search_path}")
        
        # Listar esquemas
        print("\n📁 ESQUEMAS EN LA BD:")
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_owner != 'pg_database_owner'
            ORDER BY schema_name
        """)
        for schema in cursor.fetchall():
            print(f"  - {schema[0]}")
        
        # Listar tablas en el esquema uesvalle
        print("\n📋 TABLAS EN ESQUEMA 'uesvalle':")
        cursor.execute("""
            SELECT tablename 
            FROM pg_catalog.pg_tables 
            WHERE schemaname = 'uesvalle'
            ORDER BY tablename
        """)
        tables = cursor.fetchall()
        if tables:
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("  ❌ No hay tablas en el esquema 'uesvalle'")
        
        # Listar tablas en PUBLIC
        print("\n📋 TABLAS EN ESQUEMA 'public':")
        cursor.execute("""
            SELECT tablename 
            FROM pg_catalog.pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        public_tables = cursor.fetchall()
        if public_tables:
            for table in public_tables:
                print(f"  - {table[0]}")
        else:
            print("  ❌ No hay tablas en el esquema 'public'")
        
        # Listar VISTAS en uesvalle
        print("\n👁️  VISTAS EN ESQUEMA 'uesvalle':")
        cursor.execute("""
            SELECT viewname 
            FROM pg_catalog.pg_views 
            WHERE schemaname = 'uesvalle'
            ORDER BY viewname
        """)
        views = cursor.fetchall()
        if views:
            for view in views:
                print(f"  - {view[0]}")
        else:
            print("  ❌ No hay vistas en el esquema 'uesvalle'")
        
        # Verificar estructura de tabla específica
        print("\n🔎 VERIFICACIÓN DE TABLA 'dim_municipio':")
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'uesvalle' 
                AND table_name = 'dim_municipio'
            )
        """)
        exists = cursor.fetchone()[0]
        if exists:
            print("  ✅ Tabla 'dim_municipio' existe")
            
            # Ver columnas
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'uesvalle'
                AND table_name = 'dim_municipio'
                ORDER BY ordinal_position
            """)
            print("  Columnas:")
            for col in cursor.fetchall():
                print(f"    - {col[0]}: {col[1]} (nullable: {col[2]})")
        else:
            print("  ❌ Tabla 'dim_municipio' NO existe")
        
        # Contar registros si existe
        try:
            cursor.execute("SELECT COUNT(*) FROM uesvalle.dim_municipio")
            count = cursor.fetchone()[0]
            print(f"  📊 Total registros: {count}")
        except Exception as e:
            print(f"  ⚠️  Error contando registros: {e}")
        
        # Mostrar primeros registros
        try:
            cursor.execute("SELECT * FROM uesvalle.dim_municipio LIMIT 3")
            columns = [desc[0] for desc in cursor.description]
            print(f"  Primeros registros ({', '.join(columns)}):")
            for row in cursor.fetchall():
                print(f"    {row}")
        except Exception as e:
            print(f"  ⚠️  Error mostrando registros: {e}")

except Exception as e:
    print(f"\n❌ Error de conexión: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

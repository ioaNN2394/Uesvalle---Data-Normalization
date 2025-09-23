#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

from django.db import connection

def check_tables():
    cursor = connection.cursor()
    
    print("🔍 Verificando esquemas disponibles...")
    cursor.execute("SELECT schema_name FROM information_schema.schemata;")
    schemas = cursor.fetchall()
    print("Esquemas encontrados:")
    for schema in schemas:
        print(f"  - {schema[0]}")
    
    print("\n🔍 Verificando tablas con 'institucion' en el nombre...")
    cursor.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_name LIKE '%institucion%';")
    tables = cursor.fetchall()
    print("Tablas encontradas:")
    for table in tables:
        print(f"  - {table[0]}.{table[1]}")
    
    print("\n🔍 Verificando todas las tablas en esquema 'uesvalle'...")
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'uesvalle';")
    uesvalle_tables = cursor.fetchall()
    print("Tablas en esquema 'uesvalle':")
    for table in uesvalle_tables:
        print(f"  - {table[0]}")

if __name__ == '__main__':
    check_tables()
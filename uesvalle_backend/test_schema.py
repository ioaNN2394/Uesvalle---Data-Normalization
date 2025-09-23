#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

from django.db import connection

def test_search_path():
    cursor = connection.cursor()
    
    print("🔍 Verificando search_path actual...")
    cursor.execute("SHOW search_path;")
    search_path = cursor.fetchone()
    print(f"Search path: {search_path[0]}")
    
    print("\n🔍 Probando consulta directa a uesvalle.institucion...")
    try:
        cursor.execute("SELECT COUNT(*) FROM uesvalle.institucion;")
        count = cursor.fetchone()
        print(f"✅ Número de instituciones: {count[0]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🔍 Probando consulta sin esquema explícito...")
    try:
        cursor.execute("SELECT COUNT(*) FROM institucion;")
        count = cursor.fetchone()
        print(f"✅ Número de instituciones (sin esquema): {count[0]}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_search_path()
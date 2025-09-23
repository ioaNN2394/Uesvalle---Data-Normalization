#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

from django.db import connection

def set_search_path_manually():
    cursor = connection.cursor()
    
    print("🔧 Configurando search_path manualmente...")
    cursor.execute("SET search_path = uesvalle, public, extensions;")
    
    print("🔍 Verificando search_path después del cambio...")
    cursor.execute("SHOW search_path;")
    search_path = cursor.fetchone()
    print(f"Search path: {search_path[0]}")
    
    print("\n🔍 Probando consulta sin esquema explícito después del cambio...")
    try:
        cursor.execute("SELECT COUNT(*) FROM institucion;")
        count = cursor.fetchone()
        print(f"✅ Número de instituciones: {count[0]}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    set_search_path_manually()
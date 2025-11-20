#!/usr/bin/env python
"""
Script para verificar que los endpoints del mapa funcionan correctamente.
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

from django.test import Client
from apps.etl.models import Institucion, Sede
import json

def test_map_endpoints():
    print("=" * 60)
    print("🗺️  TEST: Endpoints del Mapa")
    print("=" * 60)
    
    client = Client()
    
    # 1. Test GET /api/map/markers/
    print("\n1. Testing GET /api/map/markers/")
    print("-" * 40)
    try:
        response = client.get('/api/map/markers/')
        data = json.loads(response.content)
        
        if response.status_code == 200:
            print(f"✓ Status: 200 OK")
            print(f"✓ Marcadores retornados: {data['count']}")
            
            if data['count'] > 0:
                first_marker = data['data'][0]
                print(f"✓ Ejemplo marcador:")
                print(f"    - Institución: {first_marker['institucion']}")
                print(f"    - Sede: {first_marker['sede']}")
                print(f"    - Coordenadas: ({first_marker['lat']}, {first_marker['lon']})")
            else:
                print("⚠️  No hay marcadores en la BD (normal si está vacía)")
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"Response: {data}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 2. Test GET /api/map/institucion/<id>/
    print("\n2. Testing GET /api/map/institucion/<id>/")
    print("-" * 40)
    try:
        # Obtener una institución existente
        institucion = Institucion.objects.first()
        
        if institucion:
            url = f'/api/map/institucion/{institucion.id}/'
            response = client.get(url)
            data = json.loads(response.content)
            
            if response.status_code == 200:
                print(f"✓ Status: 200 OK")
                print(f"✓ Institución: {data['institucion']['nombre']}")
                print(f"✓ DANE: {data['institucion']['dane_ie_id']}")
                print(f"✓ Sedes: {len(data['institucion']['sedes'])}")
                
                if data['institucion']['sedes']:
                    first_sede = data['institucion']['sedes'][0]
                    print(f"  - Ejemplo sede: {first_sede['nombre']}")
            else:
                print(f"❌ Status: {response.status_code}")
        else:
            print("⚠️  No hay instituciones en la BD")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 3. Test 404 para institución inexistente
    print("\n3. Testing 404 para institución inexistente")
    print("-" * 40)
    try:
        url = '/api/map/institucion/00000000-0000-0000-0000-000000000000/'
        response = client.get(url)
        
        if response.status_code == 404:
            print(f"✓ Status: 404 Not Found (correcto)")
        else:
            print(f"❌ Status: {response.status_code} (esperaba 404)")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Tests completados")
    print("=" * 60)

if __name__ == "__main__":
    test_map_endpoints()

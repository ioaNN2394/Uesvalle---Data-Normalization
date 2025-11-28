"""
Script para probar el ETL manualmente.
Ejecutar: python test_etl.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

import pandas as pd
from django.db import connections
from apps.etl.services.orchestrator import ETLOrchestrator
from apps.etl.models import ETLRun, Institucion, Visita

def main():
    print("=" * 60)
    print("PRUEBA ETL MANUAL")
    print("=" * 60)
    
    # Crear ETLRun dummy
    etl_run = ETLRun.objects.create(status='running', meta={})
    print(f"ETLRun creado: {etl_run.id}")
    
    # Ejecutar orchestrator
    orchestrator = ETLOrchestrator(etl_run_id=etl_run.id)
    
    # Extraer datos de MySQL directamente
    print("\n📊 Extrayendo datos de MySQL...")
    conn = connections['source_mysql']
    if conn.connection is None:
        conn.connect()
    df_mysql = pd.read_sql('SELECT * FROM visitas_instituciones_educativos', conn.connection)
    df_mysql.columns = [c.lower() for c in df_mysql.columns]
    print(f"   Total filas MySQL: {len(df_mysql)}")
    
    # Verificar columnas
    print(f"   Columna nombreestablecimiento presente: {'nombreestablecimiento' in df_mysql.columns}")
    
    # Contar instituciones únicas
    df_unique = df_mysql.drop_duplicates(subset=['identificacion', 'nombreestablecimiento'])
    print(f"   Instituciones únicas (id+nombre): {len(df_unique)}")
    
    # Ejecutar bulk create instituciones (sin CSV)
    print("\n🏫 Creando instituciones...")
    inst_created, inst_updated = orchestrator._bulk_create_instituciones(df_mysql, {})
    print(f"   Creadas: {inst_created}, Actualizadas: {inst_updated}")
    
    # Ejecutar bulk create visitas
    print("\n📝 Creando visitas...")
    visitas_created, visitas_updated = orchestrator._bulk_create_visitas(df_mysql)
    print(f"   Creadas: {visitas_created}, Actualizadas: {visitas_updated}")
    
    # Verificar resultados
    print("\n" + "=" * 60)
    print("RESULTADOS FINALES")
    print("=" * 60)
    print(f"Total instituciones en BD: {Institucion.objects.count()}")
    print(f"Total visitas en BD: {Visita.objects.count()}")
    
    # Marcar ETLRun como completado
    etl_run.status = 'completed'
    etl_run.save()
    
    print("\n✅ ETL completado")

if __name__ == '__main__':
    main()

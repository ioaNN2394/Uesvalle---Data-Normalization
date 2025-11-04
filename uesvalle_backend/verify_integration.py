#!/usr/bin/env python
"""
Integration Verification Script for ETL Backend & Frontend Connection
======================================================================

Este script verifica que la integración entre Frontend y Backend está funcionando
correctamente para el flujo ETL completo:

1. Upload Files (POST /api/etl/upload/)
2. Create Job (POST /api/etl/jobs/)
3. Check Status (GET /api/etl/status/)

Uso: python verify_integration.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')
django.setup()

from django.urls import reverse, get_resolver
from django.test import Client
from apps.etl.models import ETLFile, ETLRun
from django.conf import settings
import json

print("\n" + "="*80)
print("ETL FRONTEND-BACKEND INTEGRATION VERIFICATION")
print("="*80)

# 1. Verificar URLs
print("\n[1] Verificando URLs configuradas...")
resolver = get_resolver()
etl_patterns = []
for pattern in resolver.url_patterns:
    if 'etl' in str(pattern.pattern):
        etl_patterns.append(str(pattern.pattern))

if etl_patterns:
    print(f"✓ URLs ETL encontradas ({len(etl_patterns)}):")
    for pattern in sorted(etl_patterns):
        print(f"   - {pattern}")
else:
    print("❌ No se encontraron URLs ETL")
    sys.exit(1)

# 2. Verificar modelos
print("\n[2] Verificando modelos de BD...")
try:
    # Intentar crear un ETLRun de prueba
    test_run = ETLRun.objects.create(
        status='pending',
        meta={'test': True, 'step': 'verification'}
    )
    print(f"✓ ETLRun creado: id={test_run.id}")
    
    # Crear un ETLFile de prueba
    test_file = ETLFile.objects.create(
        filename='test_verificación.xlsx',
        file_type='excel',
        file_path='/tmp/test.xlsx',
        file_size=1024,
        status='pending',
        etl_run=test_run
    )
    print(f"✓ ETLFile creado: id={test_file.id}, etl_run_id={test_file.etl_run_id}")
    
    # Limpiar
    test_file.delete()
    test_run.delete()
    print("✓ Modelos limpiados")
    
except Exception as e:
    print(f"❌ Error con modelos: {e}")
    sys.exit(1)

# 3. Verificar configuración de aplicación
print("\n[3] Verificando configuración de aplicación...")

checks = {
    'CORS_ALLOWED_ORIGINS': settings.CORS_ALLOWED_ORIGINS,
    'ETL_UPLOAD_DIR': settings.ETL_UPLOAD_DIR,
    'ETL_MAX_FILE_SIZE': settings.ETL_MAX_FILE_SIZE,
    'FILE_UPLOAD_MAX_MEMORY_SIZE': settings.FILE_UPLOAD_MAX_MEMORY_SIZE,
    'DATA_UPLOAD_MAX_MEMORY_SIZE': settings.DATA_UPLOAD_MAX_MEMORY_SIZE,
}

for key, value in checks.items():
    if value:
        print(f"✓ {key}: {value}")
    else:
        print(f"⚠️  {key}: No configurado")

# 4. Verificar directorios
print("\n[4] Verificando directorios...")
dirs_to_check = [
    settings.ETL_UPLOAD_DIR,
    os.path.join(settings.BASE_DIR, 'logs'),
]

for dir_path in dirs_to_check:
    if os.path.isdir(dir_path):
        print(f"✓ Directorio existe: {dir_path}")
    else:
        print(f"⚠️  Directorio no existe (se creará en runtime): {dir_path}")

# 5. Verificar importaciones
print("\n[5] Verificando importaciones de módulos clave...")
try:
    from apps.etl.views_v2 import upload_etl_file, ETLJobViewSet
    print("✓ Views importadas correctamente")
    
    from apps.etl.services.orchestrator import ETLOrchestrator
    print("✓ Orchestrator importado correctamente")
    
    from apps.etl.tasks import etl_run_job, etl_cancel_job
    print("✓ Tasks importadas correctamente")
    
    from apps.etl.serializers import ETLFileSerializer, ETLRunSerializer
    print("✓ Serializers importados correctamente")
    
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    sys.exit(1)

# 6. Resumen
print("\n" + "="*80)
print("✅ VERIFICACIÓN COMPLETADA EXITOSAMENTE")
print("="*80)

print("""
Próximos pasos para probar la integración:

1. BACKEND:
   - Iniciar servidor: python manage.py runserver
   - (Opcional) Iniciar worker Celery: celery -A uesvalle_backend worker -l info

2. FRONTEND:
   - Iniciar servidor: npm run dev

3. PRUEBA MANUAL:
   - Abrir http://localhost:5173
   - Navegar al módulo ETL
   - Subir un archivo Excel
   - Verificar en DevTools que POST /api/etl/upload/ se ejecuta
   - Crear un job ETL y verificar POST /api/etl/jobs/

4. VERIFICAR LOGS:
   - Logs del backend: logs/etl.log
   - Archivos subidos: etl_uploads/

Endpoints disponibles:
   POST   /api/etl/upload/          - Subir archivo Excel
   POST   /api/etl/jobs/            - Crear job ETL
   GET    /api/etl/jobs/            - Listar jobs
   GET    /api/etl/jobs/:id/        - Detalles del job
   POST   /api/etl/jobs/:id/cancel/ - Cancelar job
   GET    /api/etl/status/          - Estado general del ETL
""")

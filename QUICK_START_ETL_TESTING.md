#!/usr/bin/env python
"""
QUICK START: ETL System Testing
================================

Este script es una guía rápida para probar el sistema ETL completo
después de la implementación.

REQUISITOS PREVIOS:
===================
1. Python 3.9+
2. PostgreSQL/Supabase configurado en .env
3. Redis (para Celery, opcional)
4. Node.js 16+ (para frontend)

PASOS:
======

1. BACKEND - Inicial Setup
   ---------------------
   cd uesvalle_backend
   
   # Crear migraciones (si es primera vez)
   python manage.py makemigrations
   
   # Aplicar migraciones
   python manage.py migrate
   
   # Crear superuser (opcional)
   python manage.py createsuperuser
   
   # Verificar que no hay errores
   python manage.py check

2. BACKEND - Iniciar Servidor
   -------------------------
   # Terminal 1: API Server
   python manage.py runserver
   # Debería escuchar en http://localhost:8000
   
   # Terminal 2: Celery Worker (opcional pero recomendado)
   celery -A uesvalle_backend worker -l info
   
   # Terminal 3: Monitoring logs
   tail -f logs/etl.log

3. FRONTEND - Setup
   ----------------
   cd frontend
   npm install  # Si es primera vez
   npm run dev
   # Debería estar en http://localhost:5173

4. PRUEBA MANUAL
   ---------------
   
   a) Abrir http://localhost:5173 en navegador
   
   b) Abrir DevTools (F12)
      - Ir a Network tab
      - Filtrar por "etl"
      
   c) Encontrar módulo ETL
      - Click en "Subir Archivos"
      - O en componente de carga si existe
      
   d) Seleccionar archivo Excel
      - O arrastrar y soltar (.xlsx, .xls)
      
   e) Verificar en DevTools:
      ✓ POST /api/etl/upload/ → 200 OK
      ✓ Respuesta tiene "uploaded" array con IDs
      
   f) Click en "Procesar" o "Iniciar"
      ✓ POST /api/etl/jobs/ → 202 Accepted
      ✓ Respuesta tiene "id" del job
      
   g) Verificar logs en Terminal 3:
      ✓ "▶ Iniciando ETL job..."
      ✓ "📥 FASE 1: Extrayendo datos..."
      ✓ "✓ Excel: N registros extraídos"

5. VERIFICAR DATOS EN BD
   ----------------------
   # En otra terminal Django shell:
   python manage.py shell
   
   # Verificar archivos subidos
   >>> from apps.etl.models import ETLFile
   >>> ETLFile.objects.all()
   <QuerySet [<ETLFile: instituciones.xlsx (excel)>]>
   
   # Verificar jobs creados
   >>> from apps.etl.models import ETLRun
   >>> ETLRun.objects.all()
   <QuerySet [<ETLRun: ETL Run 1 - completed (2024-01-15 10:00:00+00:00)>]>

COMANDOS ÚTILES:
================

# Ver URLs disponibles
python manage.py help

# Migraciones
python manage.py makemigrations <app>
python manage.py migrate
python manage.py showmigrations

# Shell interactivo
python manage.py shell

# Limpiar cache
python manage.py clear_cache  # Si existe

# Revisar settings
python manage.py diffsettings

TROUBLESHOOTING:
================

1. CORS Error en Frontend
   └─ Verificar CORS_ALLOWED_ORIGINS en settings.py
   └─ Debe incluir http://localhost:5173

2. Error 413 en Upload (payload too large)
   └─ Aumentar FILE_UPLOAD_MAX_MEMORY_SIZE en settings.py
   └─ Aumentar DATA_UPLOAD_MAX_MEMORY_SIZE

3. Archivo no se guarda
   └─ Verificar que directorio etl_uploads/ existe
   └─ Revisar logs/etl.log para más detalles

4. Job se queda en "queued"
   └─ Verificar que Celery worker está corriendo
   └─ Revisar que Redis está disponible
   └─ En desarrollo, usar CELERY_TASK_ALWAYS_EAGER = True en settings

5. Error de conexión a Supabase
   └─ Verificar SUPABASE_DB_* en .env
   └─ Verificar que firewall permite conexión
   └─ Usar psql para conectar y verificar credenciales

ARCHIVOS DE CONFIGURACIÓN CLAVE:
=================================

.env (en uesvalle_backend/)
├─ SUPABASE_DB_NAME
├─ SUPABASE_DB_USER
├─ SUPABASE_DB_PASSWORD
├─ SUPABASE_DB_HOST
├─ CELERY_BROKER_URL (redis://localhost:6379/0)
└─ DEBUG (True en desarrollo)

settings.py
├─ INSTALLED_APPS
├─ MIDDLEWARE (corsheaders incluido)
├─ DATABASES
├─ REST_FRAMEWORK
├─ CORS_ALLOWED_ORIGINS
├─ LOGGING
└─ Configuración ETL_*

ENDPOINTS DEL API:
==================

POST   /api/etl/upload/
       Subir archivos Excel
       Content-Type: multipart/form-data
       Field: 'file' (puede ser múltiple)
       Response: { uploaded: [...], failed: 0 }

POST   /api/etl/jobs/
       Crear job ETL
       Content-Type: application/json
       Body: { file_ids: [...], dry_run: false, cancel_on_error: true }
       Response: { id, status, meta, ... }

GET    /api/etl/jobs/
       Listar todos los jobs
       Query: ?status=running&ordering=-started_at
       Response: [{ id, status, ... }]

GET    /api/etl/jobs/:id/
       Obtener detalles de un job
       Response: { id, status, started_at, finished_at, meta, ... }

POST   /api/etl/jobs/:id/cancel/
       Cancelar un job
       Response: { status: "cancelled" }

GET    /api/etl/status/
       Estado general del sistema ETL
       Response: { total_jobs, running_jobs, success_rate, ... }

PRÓXIMAS VALIDACIONES:
======================

- [ ] Frontend conecta correctamente a backend (sin CORS errors)
- [ ] Archivos Excel se suben sin errores
- [ ] Base de datos recibe ETLFile y ETLRun
- [ ] Logs muestran ejecución del ETL
- [ ] Job pasa por fases: extraction → transformation → loading
- [ ] Status endpoint devuelve métricas correctas
- [ ] Cancelación de jobs funciona
- [ ] Manejo de errores es robusto

¡Lista para testing!
"""

print(__doc__)

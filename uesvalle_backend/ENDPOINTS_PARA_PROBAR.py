"""
GUÍA DE ENDPOINTS PARA PROBAR EL BACKEND UESVALLE
Todos los endpoints disponibles con ejemplos de uso
"""

# ============================================================================
# 1. ENDPOINTS DE ESTADO Y SALUD
# ============================================================================

"""
✅ VERIFICAR SALUD DEL SERVIDOR

GET http://localhost:8000/api/

Respuesta esperada:
{
  "message": "API ETL UESVALLE - Sistema de Normalización de Datos Educativos",
  "version": "1.0.0",
  "endpoints": {
    "etl": "/api/etl/",
    "reports": "/api/reports/",
    "admin": "/admin/",
    "health": "/api/etl/health/",
    "docs": null
  }
}
"""

# ============================================================================
# 2. ENDPOINTS ETL (ETL Module)
# ============================================================================

"""
✅ ESTADO GENERAL DEL ETL

GET http://localhost:8000/api/etl/status/

Respuesta esperada:
{
  "total_jobs": 3,
  "running_jobs": 0,
  "success_jobs": 2,
  "failed_jobs": 1,
  "last_job": {
    "id": 123,
    "status": "success",
    "started_at": "2025-11-04T10:00:00Z",
    "finished_at": "2025-11-04T10:05:00Z"
  }
}
"""

# ============================================================================

"""
✅ LISTAR TODOS LOS JOBS ETL

GET http://localhost:8000/api/etl/jobs/

Parámetros opcionales:
- ?status=success      (filtrar por estado)
- ?status=failed
- ?status=running
- ?limit=10            (límite de resultados)
- ?page=2              (paginación)

Respuesta esperada:
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "status": "success",
      "started_at": "2025-11-04T10:00:00Z",
      "finished_at": "2025-11-04T10:05:00Z",
      "meta": {"processed_records": 150}
    },
    {
      "id": 2,
      "status": "running",
      "started_at": "2025-11-04T10:10:00Z",
      "finished_at": null,
      "meta": {"processed_records": 45}
    },
    {
      "id": 3,
      "status": "failed",
      "started_at": "2025-11-04T10:20:00Z",
      "finished_at": "2025-11-04T10:22:00Z",
      "meta": {"error": "Connection timeout"}
    }
  ]
}
"""

# ============================================================================

"""
✅ OBTENER DETALLES DE UN JOB ESPECÍFICO

GET http://localhost:8000/api/etl/jobs/{id}/

Ejemplo:
GET http://localhost:8000/api/etl/jobs/1/

Respuesta esperada:
{
  "id": 1,
  "status": "success",
  "started_at": "2025-11-04T10:00:00Z",
  "finished_at": "2025-11-04T10:05:00Z",
  "meta": {
    "processed_records": 150,
    "inserted_records": 150,
    "updated_records": 0,
    "error_records": 0
  }
}
"""

# ============================================================================

"""
✅ OBTENER ERRORES DEL ETL

GET http://localhost:8000/api/etl/jobs/{id}/errors/

Ejemplo:
GET http://localhost:8000/api/etl/jobs/3/errors/

Respuesta esperada (si hay errores):
{
  "errors": [
    {
      "row": 15,
      "field": "codigo_municipio",
      "error": "Invalid municipality code",
      "value": "INVALID123"
    },
    {
      "row": 27,
      "field": "email",
      "error": "Invalid email format",
      "value": "not-an-email"
    }
  ]
}
"""

# ============================================================================
# 3. ENDPOINTS DE DATOS (DRF Viewsets)
# ============================================================================

"""
✅ LISTAR MUNICIPIOS

GET http://localhost:8000/api/etl/municipios/

Respuesta esperada:
{
  "count": 1,
  "results": [
    {
      "codigo_municipio": "76001",
      "nombre": "Cali",
      "codigo_departamento": "76",
      "created_at": "2025-11-04T10:00:00Z",
      "updated_at": "2025-11-04T10:00:00Z"
    }
  ]
}
"""

# ============================================================================

"""
✅ LISTAR INSTITUCIONES

GET http://localhost:8000/api/etl/instituciones/

Parámetros:
- ?search=cali      (buscar por nombre)
- ?estado=Activo    (filtrar por estado)

Respuesta esperada:
{
  "count": 1,
  "results": [
    {
      "id": "uuid-1234-5678",
      "nombre": "Institución Educativa Test",
      "dane_ie_id": "DANE-TEST-001",
      "sed_ie_id": "SED-TEST-001",
      "codigo_municipio": "76001",
      "direccion": "Calle Test #123",
      "estado": "Activo",
      "created_at": "2025-11-04T10:00:00Z",
      "updated_at": "2025-11-04T10:00:00Z"
    }
  ]
}
"""

# ============================================================================

"""
✅ LISTAR SEDES

GET http://localhost:8000/api/etl/sedes/

Parámetros:
- ?institucion_id=uuid  (filtrar por institución)
- ?codigo_municipio=76001  (filtrar por municipio)

Respuesta esperada:
{
  "count": 1,
  "results": [
    {
      "id": "uuid-sede-123",
      "institucion_id": "uuid-inst-123",
      "nombre": "Sede Principal",
      "dane_sede_id": "DANE-SEDE-001",
      "codigo_municipio": "76001",
      "direccion": "Calle Sede #456",
      "lat": "3.4372",
      "lon": "-76.5197",
      "estado": "Activo",
      "created_at": "2025-11-04T10:00:00Z",
      "updated_at": "2025-11-04T10:00:00Z"
    }
  ]
}
"""

# ============================================================================

"""
✅ LISTAR MATRÍCULAS

GET http://localhost:8000/api/etl/matriculas/

Parámetros:
- ?sede_id=uuid                (filtrar por sede)
- ?corte_fecha=2025-11-04      (filtrar por fecha)
- ?nivel=Primaria              (filtrar por nivel)

Respuesta esperada:
{
  "count": 5,
  "results": [
    {
      "sede_id": "uuid-sede-123",
      "corte_fecha": "2025-11-04",
      "nivel": "Primaria",
      "grado": "1°",
      "jornada": "Mañana",
      "genero": "M",
      "total_alumnos": 30,
      "fuente": "Excel upload",
      "created_at": "2025-11-04T10:00:00Z"
    }
  ]
}
"""

# ============================================================================

"""
✅ LISTAR MATRÍCULAS ÉTNICAS

GET http://localhost:8000/api/etl/matriculas-etnicas/

Parámetros:
- ?sede_id=uuid
- ?grupo_etnico=Afrodescendiente
- ?corte_fecha=2025-11-04

Respuesta esperada:
{
  "count": 2,
  "results": [
    {
      "sede_id": "uuid-sede-123",
      "corte_fecha": "2025-11-04",
      "grupo_etnico": "Afrodescendiente",
      "total_alumnos": 8,
      "created_at": "2025-11-04T10:00:00Z"
    }
  ]
}
"""

# ============================================================================

"""
✅ LISTAR ASIGNACIONES PAE (Programa de Alimentación Escolar)

GET http://localhost:8000/api/etl/pae-asignaciones/

Parámetros:
- ?sede_id=uuid
- ?anio=2025
- ?modalidad=Desayuno

Respuesta esperada:
{
  "count": 3,
  "results": [
    {
      "sede_id": "uuid-sede-123",
      "anio": 2025,
      "periodo": "1",
      "modalidad": "Desayuno",
      "beneficiarios": 150,
      "created_at": "2025-11-04T10:00:00Z"
    }
  ]
}
"""

# ============================================================================

"""
✅ LISTAR VISITAS

GET http://localhost:8000/api/etl/visitas/

Parámetros:
- ?sede_id=uuid
- ?institucion_id=uuid
- ?fecha=2025-11-04
- ?programa=Inspección

Respuesta esperada:
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "sede_id": "uuid-sede-123",
      "institucion_id": "uuid-inst-123",
      "fecha": "2025-11-04",
      "programa": "Inspección General",
      "resultado": "Conforme",
      "observaciones": "Sistema funcionando correctamente",
      "created_at": "2025-11-04T10:00:00Z"
    }
  ]
}
"""

# ============================================================================
# 4. ENDPOINTS DE ARCHIVOS
# ============================================================================

"""
✅ LISTAR ARCHIVOS ETL

GET http://localhost:8000/api/etl/archivos/

Parámetros:
- ?status=success
- ?file_type=excel

Respuesta esperada:
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "filename": "test_data.xlsx",
      "file_type": "excel",
      "file_path": "/tmp/test_data.xlsx",
      "file_size": 102400,
      "status": "success",
      "rows_processed": 150,
      "rows_failed": 0,
      "success_rate": 100.0,
      "uploaded_at": "2025-11-04T10:00:00Z",
      "processed_at": "2025-11-04T10:05:00Z"
    }
  ]
}
"""

# ============================================================================
# 5. ENDPOINTS DE DIMENSIONES
# ============================================================================

"""
✅ LISTAR ETNIAS

GET http://localhost:8000/api/etl/etnias/

Respuesta esperada:
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "nombre": "Afrodescendiente"
    }
  ]
}
"""

"""
✅ LISTAR GRADOS

GET http://localhost:8000/api/etl/grados/

Respuesta esperada:
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "nombre": "1°"
    }
  ]
}
"""

"""
✅ LISTAR JORNADAS

GET http://localhost:8000/api/etl/jornadas/

Respuesta esperada:
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "nombre": "Mañana"
    }
  ]
}
"""

"""
✅ LISTAR NIVELES

GET http://localhost:8000/api/etl/niveles/

Respuesta esperada:
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "nombre": "Primaria"
    }
  ]
}
"""

"""
✅ LISTAR MODALIDADES PAE

GET http://localhost:8000/api/etl/modalidades-pae/

Respuesta esperada:
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "nombre": "Desayuno"
    }
  ]
}
"""

# ============================================================================
# 6. ENDPOINTS DE REPORTES (Reports Module)
# ============================================================================

"""
✅ RESUMEN DE MATRÍCULAS POR MUNICIPIO

GET http://localhost:8000/api/reports/matriculas-por-municipio/

Respuesta esperada:
{
  "results": [
    {
      "codigo_municipio": "76001",
      "nombre_municipio": "Cali",
      "total_alumnos": 500,
      "instituciones": 5,
      "sedes": 12
    }
  ]
}
"""

"""
✅ RESUMEN ÉTNICO POR SEDE

GET http://localhost:8000/api/reports/resumen-etnico/

Parámetros:
- ?sede_id=uuid

Respuesta esperada:
{
  "sede_id": "uuid-sede-123",
  "resumen": [
    {
      "grupo_etnico": "Afrodescendiente",
      "total": 50,
      "porcentaje": 15.6
    },
    {
      "grupo_etnico": "Indígena",
      "total": 25,
      "porcentaje": 7.8
    }
  ]
}
"""

"""
✅ COBERTURA PAE

GET http://localhost:8000/api/reports/cobertura-pae/

Parámetros:
- ?anio=2025
- ?municipio=76001

Respuesta esperada:
{
  "anio": 2025,
  "modalidades": [
    {
      "modalidad": "Desayuno",
      "beneficiarios": 500,
      "sedes": 12
    },
    {
      "modalidad": "Almuerzo",
      "beneficiarios": 300,
      "sedes": 8
    }
  ],
  "total_beneficiarios": 800
}
"""

# ============================================================================
# 7. ADMIN INTERFACE (Django Admin)
# ============================================================================

"""
✅ ACCEDER A ADMIN

GET http://localhost:8000/admin/

Login con credenciales creadas con:
  python manage.py createsuperuser

Desde aquí puedes:
- Ver/Editar Municipios
- Ver/Editar Instituciones
- Ver/Editar Sedes
- Ver Matrículas
- Ver Matrículas Étnicas
- Ver PAE Asignaciones
- Ver Visitas
- Ver Ejecuciones ETL
- Ver Archivos ETL
"""

# ============================================================================
# 8. PRUEBAS CON CURL (Command Line)
# ============================================================================

"""
DESDE TERMINAL/POWERSHELL:

1. Verificar salud del servidor:
   curl http://localhost:8000/api/

2. Ver estado general del ETL:
   curl http://localhost:8000/api/etl/status/

3. Listar todos los jobs:
   curl http://localhost:8000/api/etl/jobs/

4. Listar instituciones:
   curl http://localhost:8000/api/etl/instituciones/

5. Listar sedes con filtro:
   curl "http://localhost:8000/api/etl/sedes/?codigo_municipio=76001"

6. Crear nueva institución (POST):
   curl -X POST http://localhost:8000/api/etl/instituciones/ ^
     -H "Content-Type: application/json" ^
     -d {
       "nombre": "Nueva Institución",
       "dane_ie_id": "DANE-NEW-001",
       "codigo_municipio": "76001"
     }

7. Actualizar institución (PUT):
   curl -X PUT http://localhost:8000/api/etl/instituciones/uuid-123/ ^
     -H "Content-Type: application/json" ^
     -d {"estado": "Inactivo"}

8. Eliminar institución (DELETE):
   curl -X DELETE http://localhost:8000/api/etl/instituciones/uuid-123/
"""

# ============================================================================
# 9. PRUEBAS CON POSTMAN
# ============================================================================

"""
IMPORTAR EN POSTMAN:

1. Crear una nueva colección: "UESVALLE Backend"

2. Crear las siguientes requests:

📌 GET - Health Check
   URL: http://localhost:8000/api/
   
📌 GET - ETL Status
   URL: http://localhost:8000/api/etl/status/

📌 GET - List Jobs
   URL: http://localhost:8000/api/etl/jobs/
   
📌 GET - List Municipios
   URL: http://localhost:8000/api/etl/municipios/
   
📌 GET - List Instituciones
   URL: http://localhost:8000/api/etl/instituciones/
   
📌 GET - List Sedes
   URL: http://localhost:8000/api/etl/sedes/
   
📌 GET - List Matrículas
   URL: http://localhost:8000/api/etl/matriculas/
   
📌 POST - Create Institución
   URL: http://localhost:8000/api/etl/instituciones/
   Body (JSON):
   {
     "nombre": "Nueva Institución",
     "dane_ie_id": "DANE-NEW-002",
     "codigo_municipio": "76001",
     "estado": "Activo"
   }
"""

# ============================================================================
# 10. RESUMEN DE TODOS LOS ENDPOINTS
# ============================================================================

ENDPOINTS = {
    "STATE": [
        "GET  http://localhost:8000/api/",
        "GET  http://localhost:8000/api/etl/status/",
    ],
    "JOBS": [
        "GET  http://localhost:8000/api/etl/jobs/",
        "GET  http://localhost:8000/api/etl/jobs/{id}/",
        "GET  http://localhost:8000/api/etl/jobs/{id}/errors/",
    ],
    "MUNICIPIOS": [
        "GET    http://localhost:8000/api/etl/municipios/",
        "GET    http://localhost:8000/api/etl/municipios/{codigo}/",
        "POST   http://localhost:8000/api/etl/municipios/",
        "PUT    http://localhost:8000/api/etl/municipios/{codigo}/",
        "DELETE http://localhost:8000/api/etl/municipios/{codigo}/",
    ],
    "INSTITUCIONES": [
        "GET    http://localhost:8000/api/etl/instituciones/",
        "GET    http://localhost:8000/api/etl/instituciones/{id}/",
        "POST   http://localhost:8000/api/etl/instituciones/",
        "PUT    http://localhost:8000/api/etl/instituciones/{id}/",
        "DELETE http://localhost:8000/api/etl/instituciones/{id}/",
    ],
    "SEDES": [
        "GET    http://localhost:8000/api/etl/sedes/",
        "GET    http://localhost:8000/api/etl/sedes/{id}/",
        "POST   http://localhost:8000/api/etl/sedes/",
        "PUT    http://localhost:8000/api/etl/sedes/{id}/",
        "DELETE http://localhost:8000/api/etl/sedes/{id}/",
    ],
    "MATRÍCULAS": [
        "GET  http://localhost:8000/api/etl/matriculas/",
        "GET  http://localhost:8000/api/etl/matriculas-etnicas/",
    ],
    "PAE": [
        "GET  http://localhost:8000/api/etl/pae-asignaciones/",
    ],
    "VISITAS": [
        "GET  http://localhost:8000/api/etl/visitas/",
        "GET  http://localhost:8000/api/etl/visitas/{id}/",
    ],
    "DIMENSIONES": [
        "GET http://localhost:8000/api/etl/etnias/",
        "GET http://localhost:8000/api/etl/grados/",
        "GET http://localhost:8000/api/etl/jornadas/",
        "GET http://localhost:8000/api/etl/niveles/",
        "GET http://localhost:8000/api/etl/modalidades-pae/",
    ],
    "REPORTES": [
        "GET http://localhost:8000/api/reports/matriculas-por-municipio/",
        "GET http://localhost:8000/api/reports/resumen-etnico/",
        "GET http://localhost:8000/api/reports/cobertura-pae/",
    ],
    "ADMIN": [
        "GET http://localhost:8000/admin/",
    ]
}

print("\n" + "="*80)
print("📍 ENDPOINTS DISPONIBLES EN EL BACKEND UESVALLE")
print("="*80)
for category, endpoints in ENDPOINTS.items():
    print(f"\n{category}:")
    for endpoint in endpoints:
        print(f"  {endpoint}")
print("\n" + "="*80)

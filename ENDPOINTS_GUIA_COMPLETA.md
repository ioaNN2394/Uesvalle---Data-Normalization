# 🔗 GUÍA COMPLETA DE ENDPOINTS PARA PROBAR EL BACKEND

## 📌 Tabla Rápida de Todos los Endpoints

| Categoría | Método | Endpoint | Descripción |
|-----------|--------|----------|-------------|
| **Estado** | GET | `/api/` | Salud del servidor |
| **Estado** | GET | `/api/etl/status/` | Estado general del ETL |
| **Jobs** | GET | `/api/etl/jobs/` | Listar ejecuciones |
| **Jobs** | GET | `/api/etl/jobs/{id}/` | Detalles de un job |
| **Municipios** | GET | `/api/etl/municipios/` | Listar municipios |
| **Instituciones** | GET | `/api/etl/instituciones/` | Listar instituciones |
| **Sedes** | GET | `/api/etl/sedes/` | Listar sedes |
| **Matrículas** | GET | `/api/etl/matriculas/` | Listar matrículas |
| **Matrículas Étnicas** | GET | `/api/etl/matriculas-etnicas/` | Por grupo étnico |
| **PAE** | GET | `/api/etl/pae-asignaciones/` | Alimentación escolar |
| **Visitas** | GET | `/api/etl/visitas/` | Inspecciones |
| **Dimensiones** | GET | `/api/etl/etnias/` | Catálogos |
| **Reportes** | GET | `/api/reports/matriculas-por-municipio/` | Reportes |
| **Admin** | GET | `/admin/` | Panel de administración |

---

## 🧪 PRUEBAS PASO A PASO

### 1️⃣ VERIFICAR QUE EL SERVIDOR ESTÁ FUNCIONANDO

**Endpoint:**
```
GET http://localhost:8000/api/
```

**Con curl:**
```bash
curl http://localhost:8000/api/
```

**Respuesta esperada:**
```json
{
  "message": "API ETL UESVALLE - Sistema de Normalización de Datos Educativos",
  "version": "1.0.0",
  "endpoints": {
    "etl": "/api/etl/",
    "reports": "/api/reports/",
    "admin": "/admin/",
    "health": "/api/etl/health/"
  }
}
```

✅ **Si ves esto, el servidor está funcionando**

---

### 2️⃣ VER ESTADO DEL ETL

**Endpoint:**
```
GET http://localhost:8000/api/etl/status/
```

**Con curl:**
```bash
curl http://localhost:8000/api/etl/status/
```

**Respuesta esperada:**
```json
{
  "total_jobs": 3,
  "running_jobs": 0,
  "success_jobs": 2,
  "failed_jobs": 1,
  "last_job": {
    "id": 123,
    "status": "success",
    "started_at": "2025-11-04T10:00:00Z"
  }
}
```

---

### 3️⃣ LISTAR TODOS LOS JOBS (EJECUCIONES ETL)

**Endpoint:**
```
GET http://localhost:8000/api/etl/jobs/
```

**Con curl:**
```bash
curl http://localhost:8000/api/etl/jobs/
```

**Filtrar por estado:**
```bash
curl http://localhost:8000/api/etl/jobs/?status=success
curl http://localhost:8000/api/etl/jobs/?status=failed
curl http://localhost:8000/api/etl/jobs/?status=running
```

**Respuesta esperada:**
```json
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
      "meta": {
        "processed_records": 150
      }
    }
  ]
}
```

---

### 4️⃣ VER DETALLES DE UN JOB ESPECÍFICO

**Endpoint:**
```
GET http://localhost:8000/api/etl/jobs/{id}/
```

**Ejemplo:**
```bash
curl http://localhost:8000/api/etl/jobs/1/
```

**Respuesta:**
```json
{
  "id": 1,
  "status": "success",
  "started_at": "2025-11-04T10:00:00Z",
  "finished_at": "2025-11-04T10:05:00Z",
  "meta": {
    "processed_records": 150,
    "inserted_records": 150,
    "error_records": 0
  }
}
```

---

### 5️⃣ LISTAR MUNICIPIOS

**Endpoint:**
```
GET http://localhost:8000/api/etl/municipios/
```

**Con curl:**
```bash
curl http://localhost:8000/api/etl/municipios/
```

**Respuesta esperada:**
```json
{
  "count": 1,
  "results": [
    {
      "codigo_municipio": "76001",
      "nombre": "Cali",
      "codigo_departamento": "76"
    }
  ]
}
```

---

### 6️⃣ LISTAR INSTITUCIONES

**Endpoint:**
```
GET http://localhost:8000/api/etl/instituciones/
```

**Con curl:**
```bash
curl http://localhost:8000/api/etl/instituciones/
```

**Buscar específica:**
```bash
curl "http://localhost:8000/api/etl/instituciones/?search=test"
```

**Filtrar por estado:**
```bash
curl "http://localhost:8000/api/etl/instituciones/?estado=Activo"
```

**Respuesta esperada:**
```json
{
  "count": 1,
  "results": [
    {
      "id": "uuid-123",
      "nombre": "Institución Educativa Test",
      "dane_ie_id": "DANE-TEST-001",
      "codigo_municipio": "76001",
      "estado": "Activo"
    }
  ]
}
```

---

### 7️⃣ LISTAR SEDES

**Endpoint:**
```
GET http://localhost:8000/api/etl/sedes/
```

**Con curl:**
```bash
curl http://localhost:8000/api/etl/sedes/
```

**Filtrar por municipio:**
```bash
curl "http://localhost:8000/api/etl/sedes/?codigo_municipio=76001"
```

**Respuesta esperada:**
```json
{
  "count": 1,
  "results": [
    {
      "id": "uuid-sede-123",
      "nombre": "Sede Principal",
      "codigo_municipio": "76001",
      "lat": "3.4372",
      "lon": "-76.5197",
      "estado": "Activo"
    }
  ]
}
```

---

### 8️⃣ LISTAR MATRÍCULAS

**Endpoint:**
```
GET http://localhost:8000/api/etl/matriculas/
```

**Con curl:**
```bash
curl http://localhost:8000/api/etl/matriculas/
```

**Filtrar por fecha:**
```bash
curl "http://localhost:8000/api/etl/matriculas/?corte_fecha=2025-11-04"
```

**Filtrar por nivel:**
```bash
curl "http://localhost:8000/api/etl/matriculas/?nivel=Primaria"
```

---

### 9️⃣ LISTAR MATRÍCULAS ÉTNICAS

**Endpoint:**
```
GET http://localhost:8000/api/etl/matriculas-etnicas/
```

**Con curl:**
```bash
curl http://localhost:8000/api/etl/matriculas-etnicas/
```

**Filtrar por grupo étnico:**
```bash
curl "http://localhost:8000/api/etl/matriculas-etnicas/?grupo_etnico=Afrodescendiente"
```

---

### 🔟 LISTAR PAE (ALIMENTACIÓN ESCOLAR)

**Endpoint:**
```
GET http://localhost:8000/api/etl/pae-asignaciones/
```

**Con curl:**
```bash
curl http://localhost:8000/api/etl/pae-asignaciones/
```

**Filtrar por año:**
```bash
curl "http://localhost:8000/api/etl/pae-asignaciones/?anio=2025"
```

**Filtrar por modalidad:**
```bash
curl "http://localhost:8000/api/etl/pae-asignaciones/?modalidad=Desayuno"
```

---

### 1️⃣1️⃣ LISTAR VISITAS

**Endpoint:**
```
GET http://localhost:8000/api/etl/visitas/
```

**Con curl:**
```bash
curl http://localhost:8000/api/etl/visitas/
```

**Filtrar por fecha:**
```bash
curl "http://localhost:8000/api/etl/visitas/?fecha=2025-11-04"
```

---

### 1️⃣2️⃣ VER DIMENSIONES (CATÁLOGOS)

**Etnias:**
```bash
curl http://localhost:8000/api/etl/etnias/
```

**Grados:**
```bash
curl http://localhost:8000/api/etl/grados/
```

**Jornadas:**
```bash
curl http://localhost:8000/api/etl/jornadas/
```

**Niveles:**
```bash
curl http://localhost:8000/api/etl/niveles/
```

**Modalidades PAE:**
```bash
curl http://localhost:8000/api/etl/modalidades-pae/
```

---

### 1️⃣3️⃣ OPERACIONES CRUD (Crear, Actualizar, Eliminar)

**Crear una nueva institución:**
```bash
curl -X POST http://localhost:8000/api/etl/instituciones/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Nueva Institución",
    "dane_ie_id": "DANE-NEW-002",
    "codigo_municipio": "76001",
    "estado": "Activo"
  }'
```

**Actualizar una institución:**
```bash
curl -X PUT http://localhost:8000/api/etl/instituciones/uuid-123/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Nombre Actualizado",
    "estado": "Inactivo"
  }'
```

**Eliminar una institución:**
```bash
curl -X DELETE http://localhost:8000/api/etl/instituciones/uuid-123/
```

---

### 1️⃣4️⃣ REPORTES

**Matrículas por municipio:**
```bash
curl http://localhost:8000/api/reports/matriculas-por-municipio/
```

**Resumen étnico:**
```bash
curl http://localhost:8000/api/reports/resumen-etnico/
```

**Cobertura PAE:**
```bash
curl http://localhost:8000/api/reports/cobertura-pae/?anio=2025
```

---

### 1️⃣5️⃣ ADMIN INTERFACE

**Acceder a:**
```
http://localhost:8000/admin/
```

**Crear superusuario:**
```bash
python manage.py createsuperuser
```

---

## 🛠️ USAR CON HERRAMIENTAS

### Con PowerShell (Windows):

```powershell
# Verificar estado
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/" -ContentType "application/json"
$response.Content | ConvertFrom-Json

# Listar instituciones
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/etl/instituciones/"
$response.Content | ConvertFrom-Json
```

### Con Postman:

1. **Crear colección**: "UESVALLE API"
2. **Crear requests** para cada endpoint
3. **Guardar ejemplos** de respuestas
4. **Crear tests** automáticos

### Con Python:

```python
import requests

# Verificar estado
response = requests.get('http://localhost:8000/api/')
print(response.json())

# Listar instituciones
response = requests.get('http://localhost:8000/api/etl/instituciones/')
print(response.json())

# Crear institución
data = {
    'nombre': 'Nueva Institución',
    'dane_ie_id': 'DANE-NEW-003',
    'codigo_municipio': '76001'
}
response = requests.post('http://localhost:8000/api/etl/instituciones/', json=data)
print(response.json())
```

---

## ✅ CHECKLIST DE PRUEBAS

- [ ] GET `/api/` - Servidor respondiendo
- [ ] GET `/api/etl/status/` - Estado del ETL visible
- [ ] GET `/api/etl/jobs/` - Jobs listados correctamente
- [ ] GET `/api/etl/municipios/` - Municipios visibles (mínimo 1)
- [ ] GET `/api/etl/instituciones/` - Instituciones visibles
- [ ] GET `/api/etl/sedes/` - Sedes visibles
- [ ] GET `/api/etl/matriculas/` - Matrículas visibles
- [ ] POST `/api/etl/instituciones/` - Crear institución funciona
- [ ] PUT `/api/etl/instituciones/{id}/` - Actualizar funciona
- [ ] DELETE `/api/etl/instituciones/{id}/` - Eliminar funciona
- [ ] GET `/admin/` - Admin accessible (después de crear superusuario)

---

## 🎯 CONCLUSIÓN

**Si todos estos endpoints responden correctamente, tu backend está 100% operacional.**

**Recomendación:** Usa Postman o Thunder Client (VS Code) para hacer las pruebas de forma visual.

---

**¿Tienes dudas de algún endpoint específico?** 🚀

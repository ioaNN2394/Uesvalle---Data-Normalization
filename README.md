# 🏛️ Uesvalle ETL Platform

**Sistema completo de Extract-Transform-Load para normalización de datos educativos del Valle del Cauca**

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen)]()
[![License](https://img.shields.io/badge/license-Proprietary-red)]()

## 🚀 Quick Start

```bash
# 1. Instalar dependencias
pip install -r uesvalle_backend/requirements.txt

# 2. Iniciar Redis
redis-server

# 3. Iniciar Celery Worker (en terminal separada)
cd uesvalle_backend
celery -A uesvalle_backend worker -l info

# 4. Iniciar Django (en terminal separada)
python manage.py runserver

# 5. Iniciar Frontend (en terminal separada)
cd frontend
npm install && npm run dev

# 6. Crear job ETL
curl -X POST http://localhost:8000/api/etl/jobs/ \
  -H "Content-Type: application/json" \
  -d '{"file_ids": [1], "dry_run": false}'
```

Detalles: Ver [QUICK_START_BACKEND.md](uesvalle_backend/QUICK_START_BACKEND.md)

---

## 📋 Features

### ✨ Backend ETL

| Feature | Status | Details |
|---------|--------|---------|
| **Data Extraction** | ✅ Complete | MySQL, Excel, Multi-source |
| **Data Validation** | ✅ Complete | Rules engine, pattern matching |
| **Data Normalization** | ✅ Complete | Uppercase, trim, type conversion |
| **Change Detection** | ✅ Complete | SHA-256 hashing per row |
| **Atomic Loading** | ✅ Complete | ON CONFLICT upsert, transactions |
| **Async Processing** | ✅ Complete | Celery + Redis task queue |
| **REST API** | ✅ Complete | Django REST Framework |
| **Error Handling** | ✅ Complete | Retry logic, detailed logging |
| **Auditing** | ✅ Complete | ChangeLog, ETLError, Metrics |

### 🎨 Frontend

| Feature | Status | Details |
|---------|--------|---------|
| **File Upload** | ✅ Complete | Drag & drop modal |
| **Progress Tracking** | ✅ Complete | Per-file progress bars |
| **Accessibility** | ✅ Complete | WCAG 2.1 AA compliant |
| **Error Display** | ✅ Complete | User-friendly messages |
| **Real-time Status** | ✅ Complete | Poll-based updates |

### 📚 Documentation

| Document | Lines | Topics |
|----------|-------|--------|
| [Architecture](ARCHITECTURE.md) | 500+ | Design patterns, security, performance |
| [Backend Guide](uesvalle_backend/ETL_BACKEND_GUIDE.md) | 600+ | Setup, API, testing, monitoring |
| [Frontend Guide](frontend/ETL_UPLOAD_DOCUMENTATION.md) | 500+ | Components, accessibility, API contracts |
| [Deployment](DEPLOYMENT.md) | 350+ | Local, staging, production, rollback |
| [Next Steps](NEXT_STEPS.md) | 300+ | Roadmap, testing checklist, enhancements |
| [Changelog](CHANGELOG.md) | 300+ | Version history, features, improvements |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────┐
│           Vue 3 Frontend (TypeScript)              │
│    ETL Upload Modal + Drag & Drop + Progress       │
└────────────────┬────────────────────────────────────┘
                 │ HTTP POST /api/etl/jobs/
                 ▼
┌─────────────────────────────────────────────────────┐
│        Django REST Backend (DRF)                   │
│    API Layer + Service Layer + Celery Integration  │
└────────────────┬────────────────────────────────────┘
                 │ Enqueue Task
                 ▼
┌─────────────────────────────────────────────────────┐
│   Celery Worker + Redis Message Broker            │
│        Task Execution + Retry Logic               │
└────────────────┬────────────────────────────────────┘
                 │ Execute
                 ▼
┌─────────────────────────────────────────────────────┐
│        ETL Orchestrator (E → T → L)               │
│  Extract | Transform | Load | Audit              │
└────────────────┬────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
 MySQL      Supabase     Django Models
 (Legacy)  (PostgreSQL)  (Audit Trail)
```

---

## 📁 Project Structure

```
.
├── frontend/                          # Vue 3 + TypeScript
│   ├── src/
│   │   ├── modules/etl/               # ETL Upload Module
│   │   │   ├── components/            # Vue components (4 files)
│   │   │   ├── services/              # Upload service
│   │   │   └── composables/           # Reusable logic
│   │   └── components/Sidebar.vue     # ETL button integration
│   └── ETL_UPLOAD_DOCUMENTATION.md
│
├── uesvalle_backend/                  # Django 4.2+
│   ├── apps/etl/                      # ETL App
│   │   ├── services/
│   │   │   ├── __init__.py            # Base classes, utilities (540 LOC)
│   │   │   ├── extractors.py          # MySQL, Excel, Multi-source (380 LOC)
│   │   │   ├── transformers.py        # Validation, normalization (450 LOC)
│   │   │   └── loaders.py             # PostgreSQL, Supabase (350 LOC)
│   │   ├── orchestrator.py            # E-T-L coordination (420 LOC)
│   │   ├── tasks.py                   # Celery tasks (280 LOC)
│   │   ├── views_v2.py                # REST endpoints (260 LOC)
│   │   ├── models.py                  # Data models
│   │   └── urls.py                    # API routes
│   ├── uesvalle_backend/
│   │   ├── celery.py                  # Celery config
│   │   ├── settings.py                # Django settings + Celery
│   │   └── __init__.py                # Celery import
│   ├── requirements.txt                # Dependencies
│   ├── ETL_BACKEND_GUIDE.md            # 600+ line guide
│   └── QUICK_START_BACKEND.md          # Quick setup
│
├── ARCHITECTURE.md                    # Technical deep dive
├── DEPLOYMENT.md                      # Production guide
├── CHANGELOG.md                       # Version history
├── NEXT_STEPS.md                      # Roadmap & tasks
└── README.md                          # This file
```

---

## 🔧 Technology Stack

### Backend
- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL (Supabase) + MySQL (legacy)
- **Task Queue**: Celery + Redis
- **ETL**: Pandas + SQLAlchemy
- **ORM**: Django ORM with multi-DB support

### Frontend
- **Framework**: Vue 3 with `<script setup>`
- **Language**: TypeScript (strict mode)
- **Build Tool**: Vite
- **Styling**: CSS3 with Tailwind-like utilities
- **Accessibility**: WCAG 2.1 AA compliant

### Infrastructure
- **Message Broker**: Redis 7+
- **Database**: Supabase (PostgreSQL 14+), MySQL 8+
- **Monitoring**: Flower (Celery dashboard)
- **Logging**: Python logging module

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- Redis 7+
- PostgreSQL 14+ (Supabase account)
- MySQL 8+ (for legacy data)

### Installation

```bash
# Clone repository
git clone <repo>
cd Uesvalle-Normalization

# Backend setup
cd uesvalle_backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env
cp .env.example .env
# Edit with your Supabase + MySQL credentials

# Frontend setup
cd ../frontend
npm install
```

### Running Services

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
cd uesvalle_backend
source venv/bin/activate
celery -A uesvalle_backend worker -l info

# Terminal 3: Django
cd uesvalle_backend
python manage.py runserver

# Terminal 4: Frontend
cd frontend
npm run dev

# Terminal 5: Flower (monitoring)
celery -A uesvalle_backend flower --port=5555
```

---

## 📊 API Documentation

### Create ETL Job

```bash
POST /api/etl/jobs/
Content-Type: application/json

{
  "file_ids": [1, 2],
  "dry_run": false,
  "cancel_on_error": true
}

Response: 202 Accepted
{
  "id": 1,
  "status": "queued",
  "metadata": {
    "task_id": "celery-task-uuid"
  }
}
```

### Get Job Status

```bash
GET /api/etl/jobs/1/

Response: 200 OK
{
  "id": 1,
  "status": "running",
  "metadata": {
    "progress": {
      "stage": "transformation",
      "current": 2,
      "total": 3
    }
  }
}
```

### View Logs

```bash
GET /api/etl/jobs/1/logs/?level=error&page=1

Response: 200 OK
{
  "count": 5,
  "results": [
    {
      "phase": "transformation",
      "error_type": "validation",
      "message": "Invalid DANE code"
    }
  ]
}
```

### Cancel Job

```bash
POST /api/etl/jobs/1/cancel/

Response: 200 OK
```

---

## 🧪 Testing

### Unit Tests

```bash
python manage.py test apps.etl.tests.unit
```

### Integration Tests

```bash
python manage.py test apps.etl.tests.integration
```

### API Tests

```bash
python manage.py test apps.etl.tests.api
```

### All Tests

```bash
python manage.py test
```

---

## 📈 Monitoring

### Celery Dashboard (Flower)

```
http://localhost:5555
```

Features:
- Real-time task monitoring
- Worker statistics
- Task history
- Rate limiting

### Logs

```bash
# Backend logs
tail -f uesvalle_backend/logs/etl.log

# Celery logs
tail -f /var/log/uesvalle-celery.log

# Nginx logs (production)
tail -f /var/log/nginx/error.log
```

### Django Admin

```
http://localhost:8000/admin
```

Monitor:
- ETLRun (job executions)
- ETLError (errors)
- ChangeLog (audit trail)
- DataQualityCheck (validation results)

---

## 🔐 Security

- ✅ Input validation (extension, MIME, size)
- ✅ SQL injection prevention (parameterized queries)
- ✅ CSRF protection
- ✅ CORS properly configured
- ✅ Service Role isolation
- ✅ Secure serialization (JSON vs pickle)
- ✅ Error message sanitization

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, patterns, security |
| [ETL_BACKEND_GUIDE.md](uesvalle_backend/ETL_BACKEND_GUIDE.md) | Comprehensive backend guide |
| [ETL_UPLOAD_DOCUMENTATION.md](frontend/ETL_UPLOAD_DOCUMENTATION.md) | Frontend component guide |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment |
| [NEXT_STEPS.md](NEXT_STEPS.md) | Testing & enhancement roadmap |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [QUICK_START_BACKEND.md](uesvalle_backend/QUICK_START_BACKEND.md) | 5-minute backend setup |
| [QUICK_START_ETL_UPLOAD.md](frontend/QUICK_START_ETL_UPLOAD.md) | Frontend quick start |

---

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Add/update tests
4. Update documentation
5. Submit pull request

---

## 📞 Support

For issues:

1. Check logs: `tail -f uesvalle_backend/logs/etl.log`
2. Monitor Celery: `http://localhost:5555`
3. Consult docs: `ETL_BACKEND_GUIDE.md`
4. Run tests: `python manage.py test apps.etl`

---

## 📋 License

Proprietary - Uesvalle

---

## ✅ Status

| Component | Status | Last Updated |
|-----------|--------|--------------|
| Backend | ✅ Complete | 2024-01-15 |
| Frontend | ✅ Complete | 2024-01-15 |
| Documentation | ✅ Complete | 2024-01-15 |
| Tests | ✅ Ready | 2024-01-15 |
| Deployment | ✅ Ready | 2024-01-15 |

**System is production-ready and fully documented.**

---

Última actualización: 2024-01-15 | Versión: 1.0.0
Copia y configura el archivo `.env`:

```bash
# MySQL origen (fuente de datos)
MYSQL_HOST=tu-host-mysql
MYSQL_PORT=3306
MYSQL_DB=nombre_bd
MYSQL_USER=usuario
MYSQL_PASSWORD=contraseña

# Supabase Postgres (destino normalizado)
SUPABASE_DB_HOST=tu-proyecto.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.tu_usuario
SUPABASE_DB_PASS=tu_contraseña
SUPABASE_DB_SSLMODE=require

# Supabase REST API (opcional)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu-service-key

# Django
DEBUG=True
SECRET_KEY=tu-secret-key
```

### 2. Instalación

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar migraciones (solo en Supabase/default)
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

## 🚀 Uso del Sistema

### Comando ETL (Recomendado)

```bash
# ETL completo con archivos Excel
python manage.py etl_run --excel-a=ruta/archivo_a.xlsx --excel-b=ruta/archivo_b.xlsx

# Solo MySQL
python manage.py etl_run --mysql-only

# Modo de prueba
python manage.py etl_run --dry-run --excel-a=archivo.xlsx
```

### API REST

#### Endpoints Principales

```
GET  /api/                          # Info general de la API
GET  /api/etl/health/              # Estado de conexiones
GET  /api/etl/control/status/      # Estado del ETL
POST /api/etl/control/execute/     # Ejecutar ETL

# Consulta de datos
GET  /api/etl/instituciones/       # Lista instituciones
GET  /api/etl/instituciones/for_map/ # Datos para mapa
GET  /api/etl/instituciones/statistics/ # Estadísticas
GET  /api/etl/municipios/          # Lista municipios
GET  /api/etl/runs/                # Historial de ETL
```

#### Ejecutar ETL via API

```bash
curl -X POST http://localhost:8000/api/etl/control/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "excel_a_path": "/ruta/archivo_a.xlsx",
    "excel_b_path": "/ruta/archivo_b.xlsx"
  }'
```

#### Consultar Estado

```bash
curl http://localhost:8000/api/etl/control/status/
```

### Programación Automática (Cron)

```bash
# Ejemplo: ejecutar cada día a las 3 AM
0 3 * * * cd /ruta/proyecto && /ruta/venv/bin/python manage.py etl_run --excel-a=/data/a.xlsx --excel-b=/data/b.xlsx
```

## 📊 Modelo de Datos

### Patrón Data Warehouse

#### Dimensiones (`dim_*`)
- **DimMunicipio**: Catálogo de municipios
- **DimSede**: Catálogo de sedes educativas

#### Hechos (`fact_*`)
- **FactInstitucion**: Instituciones educativas consolidadas

#### Auditoría
- **ETLRun**: Registro de ejecuciones
- **ChangeLog**: Log detallado de cambios

### Campos Principales

```python
FactInstitucion:
├── codigo_dane (único)         # Clave natural
├── nombre                      # Nombre institución
├── municipio (FK)              # Relación a DimMunicipio
├── estado                      # Activo/Inactivo/etc.
├── sector                      # Oficial/No Oficial
├── zona                        # Urbana/Rural
├── latitud, longitud           # Coordenadas para mapa
├── updated_hash                # Para detectar cambios
├── source_system               # mysql/excel_a/excel_b
└── created_at, updated_at      # Timestamps
```

## 🔄 Pipeline ETL

### 1. Extracción
- **MySQL**: Consultas SQL directas
- **Excel**: Pandas con `read_excel()`
- **Validación**: Archivos existentes, estructura

### 2. Transformación
- **Normalización**: Limpieza de strings, códigos
- **Unificación**: Merge de las 3 fuentes
- **Deduplicación**: Por `codigo_dane`
- **Hash**: Detección de cambios

### 3. Carga
- **ORM Django**: Transacciones seguras (`bulk_create/update`)
- **SQLAlchemy**: Upserts nativos PostgreSQL (mejor rendimiento)
- **Auditoría**: Log de todos los cambios

## 🛠️ Desarrollo

### Tests

```bash
python manage.py test
```

### Estructura de Tests

```python
# Ejemplo test ETL
from django.test import TestCase
from apps.etl.services import ETLOrchestrator

class ETLTest(TestCase):
    def test_mysql_extraction(self):
        # Test extracción MySQL
        pass
    
    def test_transformation(self):
        # Test transformación datos
        pass
```

### Logging

```python
import logging
logger = logging.getLogger('apps.etl')

# En settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'etl.log',
        },
    },
    'loggers': {
        'apps.etl': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 📈 Monitoreo

### Health Check

```bash
curl http://localhost:8000/api/etl/health/
```

### Métricas Disponibles

- Estado de conexiones de BD
- Últimas ejecuciones ETL
- Conteos de registros por fuente
- Estadísticas de instituciones
- Detección de errores

## 🔧 Troubleshooting

### Problemas Comunes

1. **Error de conexión MySQL**
   ```bash
   # Verificar variables de entorno
   python manage.py shell
   >>> from django.db import connections
   >>> connections['source_mysql'].cursor()
   ```

2. **Error de conexión Supabase**
   ```bash
   # Verificar SSL y credenciales
   python manage.py dbshell
   ```

3. **Archivos Excel no encontrados**
   ```bash
   # Verificar rutas absolutas
   python manage.py etl_run --dry-run --excel-a=/ruta/completa/archivo.xlsx
   ```

## 📚 Referencias

- [Documentación Django](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Supabase Docs](https://supabase.com/docs)
- [SQLAlchemy](https://docs.sqlalchemy.org/)

## 🤝 Contribución

1. Fork del proyecto
2. Crear rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para detalles.

---

**Sistema ETL UESVALLE** - Normalización de Datos Educativos  
*Desarrollado para la Universidad del Valle*
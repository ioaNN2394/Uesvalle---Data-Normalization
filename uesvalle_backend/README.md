# ETL UESVALLE - Sistema de Normalización de Datos Educativos

Sistema ETL (Extract, Transform, Load) para la normalización de datos de instituciones educativas del Valle del Cauca. Integra múltiples fuentes de datos (MySQL + Excel) para cargar información normalizada en Supabase (PostgreSQL).

## 🏗️ Arquitectura

### Fuentes de Datos
- **MySQL**: Base de datos transaccional principal
- **Excel A**: Archivo complementario A
- **Excel B**: Archivo complementario B

### Destino
- **Supabase (PostgreSQL)**: Data warehouse normalizado

### Tecnologías
- **Backend**: Django 4.2+ con Django REST Framework
- **ETL Engine**: Pandas + SQLAlchemy
- **Bases de Datos**: PostgreSQL (Supabase) + MySQL
- **APIs**: REST API con endpoints para consulta y control

## 📦 Estructura del Proyecto

```
uesvalle_backend/
├── apps/
│   ├── core/                    # Configuración central
│   │   ├── db_routers.py       # Router de múltiples BDs
│   │   └── models.py
│   ├── etl/                    # Módulo ETL principal
│   │   ├── models.py           # Modelos dim_* y fact_*
│   │   ├── services.py         # Lógica ETL
│   │   ├── serializers.py      # Serializers API
│   │   ├── views.py            # Endpoints API
│   │   ├── urls.py             # Rutas API
│   │   └── management/
│   │       └── commands/
│   │           └── etl_run.py  # Comando ETL
│   └── reports/                # Módulo de reportes
├── uesvalle_backend/
│   ├── settings.py             # Configuración Django
│   └── urls.py                 # URLs principales
├── requirements.txt            # Dependencias
├── .env                        # Variables de entorno
└── manage.py                   # Django CLI
```

## ⚙️ Configuración

### 1. Variables de Entorno

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
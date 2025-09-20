# Guía de Despliegue - ETL UESVALLE

## 🚀 Pasos de Implementación

### 1. Preparación del Entorno

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd uesvalle_backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración de Bases de Datos

#### Supabase (PostgreSQL)
1. Crear proyecto en [Supabase](https://supabase.com)
2. Obtener credenciales de conexión:
   - Host: `db.xxx.supabase.co`
   - Puerto: `5432`
   - Database: `postgres`
   - Usuario: `postgres.username`
   - Contraseña: `tu_password`

#### MySQL (Fuente de Datos)
1. Verificar acceso a la base MySQL existente
2. Confirmar tablas: `instituciones_educativas`, `municipios`
3. Verificar usuario con permisos de lectura

### 3. Configurar Variables de Entorno

```bash
# Copiar archivo ejemplo
cp .env.example .env

# Editar .env con tus credenciales reales
```

**Archivo .env completo:**
```env
# MySQL origen
MYSQL_HOST=192.168.1.244
MYSQL_PORT=3306
MYSQL_DB=siscloud
MYSQL_USER=eis2025
MYSQL_PASSWORD=Eis2025*

# Supabase Postgres
SUPABASE_DB_HOST=db.tuproyecto.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.tuusuario
SUPABASE_DB_PASS=tu_password_real
SUPABASE_DB_SSLMODE=require

# Supabase API (para funciones avanzadas)
SUPABASE_URL=https://tuproyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu_service_key_real

# Django
DEBUG=False
SECRET_KEY=genera-una-clave-secreta-segura-aqui
```

### 4. Inicializar Base de Datos

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones (solo en Supabase)
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

### 5. Verificar Instalación

```bash
# Test de conexiones
python manage.py shell
>>> from django.db import connections
>>> connections['default'].cursor()  # Supabase
>>> connections['source_mysql'].cursor()  # MySQL
>>> exit()

# Test del ETL
python manage.py etl_run --dry-run --mysql-only

# Iniciar servidor de desarrollo
python manage.py runserver
```

### 6. Verificar API

```bash
# Health check
curl http://localhost:8000/api/etl/health/

# Estado ETL
curl http://localhost:8000/api/etl/control/status/

# Lista de instituciones
curl http://localhost:8000/api/etl/instituciones/
```

## 🔧 Configuración de Producción

### 1. Servidor Web (Gunicorn + Nginx)

**gunicorn_config.py:**
```python
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
timeout = 300
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
```

**Ejecutar con Gunicorn:**
```bash
gunicorn --config gunicorn_config.py uesvalle_backend.wsgi:application
```

### 2. Nginx (Proxy Reverso)

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Programación Automática (Cron)

```bash
# Editar crontab
crontab -e

# Agregar línea para ETL diario a las 3 AM
0 3 * * * cd /ruta/proyecto && /ruta/venv/bin/python manage.py etl_run --excel-a=/data/archivo_a.xlsx --excel-b=/data/archivo_b.xlsx >> /var/log/etl_cron.log 2>&1
```

### 4. Monitoreo con Systemd

**etl-django.service:**
```ini
[Unit]
Description=ETL UESVALLE Django App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/ruta/uesvalle_backend
Environment="PATH=/ruta/venv/bin"
ExecStart=/ruta/venv/bin/gunicorn --config gunicorn_config.py uesvalle_backend.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y iniciar servicio
sudo systemctl enable etl-django.service
sudo systemctl start etl-django.service
sudo systemctl status etl-django.service
```

## 📊 Configuración de Supabase

### 1. Habilitar Row Level Security (RLS)

```sql
-- Conectar a Supabase SQL Editor
-- Habilitar RLS en tablas principales

ALTER TABLE etl_factinstitucion ENABLE ROW LEVEL SECURITY;
ALTER TABLE etl_dimunicipio ENABLE ROW LEVEL SECURITY;

-- Crear política para acceso público a lectura
CREATE POLICY "Allow public read" ON etl_factinstitucion
  FOR SELECT USING (true);

CREATE POLICY "Allow public read" ON etl_dimmunicipio
  FOR SELECT USING (true);
```

### 2. Crear Índices para Performance

```sql
-- Índices adicionales para consultas del frontend
CREATE INDEX CONCURRENTLY idx_instituciones_coordinates 
ON etl_factinstitucion (latitud, longitud) 
WHERE latitud IS NOT NULL AND longitud IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_instituciones_search 
ON etl_factinstitucion USING GIN (to_tsvector('spanish', nombre));

CREATE INDEX CONCURRENTLY idx_instituciones_municipio_estado 
ON etl_factinstitucion (municipio_id, estado);
```

## 🔍 Troubleshooting de Producción

### 1. Logs de Error

```bash
# Ver logs Django
tail -f logs/etl.log

# Ver logs sistema
sudo journalctl -u etl-django.service -f

# Ver logs Nginx
sudo tail -f /var/log/nginx/error.log
```

### 2. Problemas Comunes

**Error de conexión Supabase:**
```bash
# Verificar variables de entorno
echo $SUPABASE_DB_HOST
echo $SUPABASE_DB_USER

# Test directo de conexión
psql "postgresql://user:pass@host:5432/postgres?sslmode=require"
```

**Error de memoria en ETL:**
```python
# En settings.py, reducir chunk size
ETL_CHUNK_SIZE = 1000  # En lugar de 5000
ETL_BATCH_SIZE = 500   # En lugar de 2000
```

**Timeout en consultas:**
```python
# En settings.py, aumentar timeout
DATABASES = {
    'default': {
        # ... otras configuraciones
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 60,
        },
    }
}
```

## 📈 Monitoreo y Alertas

### 1. Health Check Automatizado

```bash
# Script para monitoreo
#!/bin/bash
# monitor_etl.sh

HEALTH_URL="http://localhost:8000/api/etl/health/"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -ne 200 ]; then
    echo "ETL Health Check Failed: $RESPONSE"
    # Enviar alerta por email/slack
fi
```

### 2. Métricas de Performance

```bash
# Cron para logs de métricas cada hora
0 * * * * curl -s http://localhost:8000/api/etl/control/status/ | jq '.' >> /var/log/etl_metrics.log
```

## 🔧 Mantenimiento

### 1. Backup de Configuración

```bash
# Backup de .env
cp .env .env.backup.$(date +%Y%m%d)

# Backup de base de datos (opcional)
pg_dump "postgresql://user:pass@host:5432/postgres" > backup_$(date +%Y%m%d).sql
```

### 2. Limpieza de Logs

```bash
# Limpiar logs antiguos
find logs/ -name "*.log" -mtime +30 -delete

# Rotar logs
logrotate -f /etc/logrotate.d/etl-django
```

### 3. Actualización del Sistema

```bash
# Actualizar código
git pull origin main

# Actualizar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py migrate

# Reiniciar servicio
sudo systemctl restart etl-django.service
```

---

**¡Instalación Completada!** 🎉

El sistema ETL UESVALLE está listo para normalizar datos educativos.

Para soporte técnico, consultar la documentación completa en README.md
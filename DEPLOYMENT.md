# Deployment Guide - ETL Backend + Frontend

## 🚀 Índice

1. [Desarrollo Local](#desarrollo-local)
2. [Deployment a Producción](#deployment-a-producción)
3. [Monitoreo y Troubleshooting](#monitoreo-y-troubleshooting)
4. [Rollback Plan](#rollback-plan)

---

## Desarrollo Local

### Requisitos

- Python 3.9+
- Node.js 18+
- Redis 7+
- PostgreSQL 14+ (o Supabase account)
- MySQL 8+ (para legacy data source)

### Setup Backend

```bash
# 1. Clonar y navegar
cd uesvalle_backend

# 2. Crear venv
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar .env
cat > .env << EOF
DEBUG=True
SECRET_KEY=your-secret-key-here

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJxxx...

# MySQL
DATABASE_URL_MYSQL=mysql://user:pass@localhost:3306/uesvalle

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# ETL
ETL_UPLOAD_DIR=/tmp/etl_uploads
EOF

# 5. Migrar BD
python manage.py migrate

# 6. Crear superuser (opcional)
python manage.py createsuperuser
```

### Iniciar Servicios

**Terminal 1: Redis**

```bash
redis-server
```

**Terminal 2: Celery Worker**

```bash
cd uesvalle_backend
celery -A uesvalle_backend worker -l info
```

**Terminal 3: Celery Flower (Monitoreo)**

```bash
cd uesvalle_backend
celery -A uesvalle_backend flower --port=5555
# http://localhost:5555
```

**Terminal 4: Django**

```bash
cd uesvalle_backend
python manage.py runserver
# http://localhost:8000
```

**Terminal 5: Frontend**

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

---

## Deployment a Producción

### 1. Preparar servidor

```bash
# Ubuntu 22.04 LTS recomendado

# Actualizar sistema
sudo apt-get update && sudo apt-get upgrade -y

# Instalar dependencias
sudo apt-get install -y \
  python3.11 python3-venv python3-dev \
  postgresql postgresql-contrib \
  redis-server \
  nginx \
  supervisor \
  git \
  curl

# Node.js (para frontend)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Crear usuario de aplicación

```bash
sudo useradd -m -s /bin/bash uesvalle
sudo usermod -aG sudo uesvalle
```

### 3. Clonar repositorio

```bash
sudo -u uesvalle -H bash << 'EOF'
cd /home/uesvalle
git clone <tu-repo> uesvalle-app
cd uesvalle-app/uesvalle_backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # Servidor WSGI production
EOF
```

### 4. Configurar variables de entorno

```bash
sudo -u uesvalle -H bash << 'EOF'
cat > /home/uesvalle/uesvalle-app/uesvalle_backend/.env << 'ENVEOF'
DEBUG=False
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJxxx...

# MySQL
DATABASE_URL_MYSQL=mysql://user:pass@mysql.example.com:3306/uesvalle

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# ETL
ETL_UPLOAD_DIR=/var/www/uesvalle/etl_uploads
ETL_MAX_FILE_SIZE=52428800

# Email (para notificaciones de errores)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
ENVEOF
EOF
```

### 5. Coleccionar static files

```bash
sudo -u uesvalle -H bash << 'EOF'
cd /home/uesvalle/uesvalle-app/uesvalle_backend
source venv/bin/activate
python manage.py collectstatic --noinput
EOF
```

### 6. Crear directorio para uploads

```bash
sudo mkdir -p /var/www/uesvalle/etl_uploads
sudo chown -R uesvalle:uesvalle /var/www/uesvalle/etl_uploads
sudo chmod -R 755 /var/www/uesvalle/etl_uploads
```

### 7. Configurar Supervisor para Django + Celery

**`/etc/supervisor/conf.d/uesvalle-django.conf`**

```ini
[program:uesvalle-django]
directory=/home/uesvalle/uesvalle-app/uesvalle_backend
command=/home/uesvalle/uesvalle-app/uesvalle_backend/venv/bin/gunicorn \
    --workers=4 \
    --worker-class=sync \
    --bind=127.0.0.1:8000 \
    --access-logfile=/var/log/uesvalle-django-access.log \
    --error-logfile=/var/log/uesvalle-django-error.log \
    --log-level=info \
    uesvalle_backend.wsgi:application

user=uesvalle
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=10
stdout_logfile=/var/log/uesvalle-django.log
stderr_logfile=/var/log/uesvalle-django.log
```

**`/etc/supervisor/conf.d/uesvalle-celery.conf`**

```ini
[program:uesvalle-celery]
directory=/home/uesvalle/uesvalle-app/uesvalle_backend
command=/home/uesvalle/uesvalle-app/uesvalle_backend/venv/bin/celery \
    -A uesvalle_backend \
    worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000

user=uesvalle
autostart=true
autorestart=true
startsecs=10
stdout_logfile=/var/log/uesvalle-celery.log
stderr_logfile=/var/log/uesvalle-celery.log
```

**Iniciar Supervisor**

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start uesvalle-django
sudo supervisorctl start uesvalle-celery
```

### 8. Configurar Nginx como reverse proxy

**`/etc/nginx/sites-available/uesvalle`**

```nginx
upstream django {
    server 127.0.0.1:8000;
}

upstream flower {
    server 127.0.0.1:5555;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    client_max_body_size 50M;

    # Redirigir HTTP a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    client_max_body_size 50M;

    # SSL certificates (usar Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Static files
    location /static/ {
        alias /var/www/uesvalle/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (uploads)
    location /media/ {
        alias /var/www/uesvalle/media/;
        expires 7d;
    }

    # Django API
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Flower (monitoreo Celery) - proteger con auth
    location /flower/ {
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://flower/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml+rss 
               application/javascript application/json;
    gzip_disable "msie6";
}
```

**Habilitar sitio**

```bash
sudo ln -s /etc/nginx/sites-available/uesvalle /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 9. Instalar certificado SSL (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
```

### 10. Build y deploy frontend

```bash
cd /home/uesvalle/uesvalle-app/frontend
npm install
npm run build
# Copiar dist a nginx
sudo cp -r dist/* /var/www/uesvalle/static/
```

---

## Monitoreo y Troubleshooting

### Verificar servicios

```bash
# Django + Gunicorn
sudo supervisorctl status uesvalle-django

# Celery Worker
sudo supervisorctl status uesvalle-celery

# Nginx
sudo systemctl status nginx

# Redis
redis-cli ping  # Debería retornar PONG
```

### Ver logs

```bash
# Django
sudo tail -f /var/log/uesvalle-django.log

# Celery
sudo tail -f /var/log/uesvalle-celery.log

# Nginx
sudo tail -f /var/log/nginx/error.log

# Sistema
sudo journalctl -u nginx -f
```

### Reiniciar servicios

```bash
# Todo
sudo supervisorctl restart all

# Individual
sudo supervisorctl restart uesvalle-django
sudo supervisorctl restart uesvalle-celery
```

### Limpiar colas Celery

```bash
cd /home/uesvalle/uesvalle-app/uesvalle_backend
source venv/bin/activate
celery -A uesvalle_backend purge
```

### Verificar estado de Celery

```bash
# Conectarse a Flower
https://yourdomain.com/flower/

# O desde línea de comandos
celery -A uesvalle_backend inspect active
celery -A uesvalle_backend inspect stats
```

---

## Rollback Plan

### Ante error crítico en producción

```bash
# 1. Parar servicios
sudo supervisorctl stop all

# 2. Restaurar versión anterior del código
cd /home/uesvalle/uesvalle-app
git reset --hard HEAD~1

# 3. Si hay cambios en BD, hacer rollback
cd uesvalle_backend
source venv/bin/activate
python manage.py migrate 0004_previous_migration

# 4. Reiniciar servicios
sudo supervisorctl start uesvalle-django
sudo supervisorctl start uesvalle-celery

# 5. Verificar
curl https://yourdomain.com/api/etl/status/
```

### Backup antes de deploy

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/uesvalle_$DATE"

mkdir -p $BACKUP_DIR

# Backup código
cp -r /home/uesvalle/uesvalle-app $BACKUP_DIR/app

# Backup BD
pg_dump -h localhost -U uesvalle_user uesvalle_db > $BACKUP_DIR/db_backup.sql

# Backup Redis
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb $BACKUP_DIR/

echo "✓ Backup completado: $BACKUP_DIR"
```

---

## Configuración de Alertas (Opcional)

### Sentry para error tracking

```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="https://xxx@xxx.ingest.sentry.io/xxx",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False
)
```

### Uptimerobot para monitoreo

```bash
# Endpoint para monitoreo
GET /api/etl/status/
# Response 200: OK
# Response 500: Alert
```

---

## Checklist Pre-Deployment

- [ ] Actualizar `.env` con credenciales correctas
- [ ] Ejecutar `collectstatic --noinput`
- [ ] Crear base de datos y ejecutar migraciones
- [ ] Probar extracción de datos (MySQL + Excel)
- [ ] Probar carga a Supabase
- [ ] Verificar Redis conexión
- [ ] Verificar Celery workers online
- [ ] Probar endpoints API
- [ ] Configurar SSL con Let's Encrypt
- [ ] Configurar backup automático
- [ ] Documentar credenciales en gestor seguro
- [ ] Establecer monitoring y alertas


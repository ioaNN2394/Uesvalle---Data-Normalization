"""
Celery Configuration
====================

Configura Celery como task queue para operaciones asincrónicas (ETL jobs).

Uso en Django:
    from uesvalle_backend.celery import app
    
Comandos:
    # Iniciar worker
    celery -A uesvalle_backend worker -l info
    
    # Iniciar flower (monitoring)
    celery -A uesvalle_backend flower
    
    # Con Redis
    redis-server
"""

import os
from celery import Celery
from django.conf import settings

# Configurar módulo settings de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uesvalle_backend.settings')

app = Celery('uesvalle_backend')

# Cargar configuración de settings.py con prefijo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tareas en apps.etl.tasks
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """Tarea de prueba para verificar que Celery funciona."""
    print(f'Request: {self.request!r}')


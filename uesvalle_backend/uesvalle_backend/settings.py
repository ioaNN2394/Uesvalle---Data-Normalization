import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configurar UTF-8 para consola Windows según documentación Python oficial
# Corrige UnicodeEncodeError con emojis en PowerShell/CMD
try:
    if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    # Fallback para versiones Python < 3.7 o errores de configuración
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'apps.core',
    'apps.etl',
    'apps.reports',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'uesvalle_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'uesvalle_backend.wsgi.application'

# Database configuration - Multiple databases for ETL
# Database routing
DATABASE_ROUTERS = ['apps.core.db_routers.DatabaseRouter']

DATABASES = {
    "default": {  # Supabase (Postgres) - destino normalizado
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("SUPABASE_DB_NAME"),
        "USER": os.getenv("SUPABASE_DB_USER"),
        "PASSWORD": os.getenv("SUPABASE_DB_PASSWORD"),
        "HOST": os.getenv("SUPABASE_DB_HOST"),
        "PORT": os.getenv("SUPABASE_DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": os.getenv("SUPABASE_DB_SSLMODE", "require"),
            # Configurar search_path según documentación PostgreSQL oficial
            "options": "-c search_path=uesvalle,public"  # uesvalle primero
        },
    },
    "source_mysql": {  # BD de origen (MySQL)
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DB"),
        "USER": os.getenv("MYSQL_USER"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD"),
        "HOST": os.getenv("MYSQL_HOST"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    },
}

# Configuración especial para tests - evitar pooler de Supabase
# Django intenta hacer DROP DATABASE pero PgBouncer mantiene conexiones abiertas
if 'test' in sys.argv:
    # Para tests, desactivar server-side cursors y no reutilizar conexiones
    # Esto evita que PgBouncer bloquee el DROP DATABASE durante teardown
    DATABASES["default"]["CONN_MAX_AGE"] = 0  # No reutilizar conexiones
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True  # Evitar cursores del lado servidor
    
    # Configuración adicional para tests
    DATABASES["default"]["TEST"] = {
        "NAME": None,  # Django creará BD de test automáticamente
        "SERIALIZE": False,  # No serializar BD para mejor performance
        "MIRROR": None,
    }
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# CORS configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_ALL_ORIGINS = DEBUG

# ETL Configuration
ETL_CHUNK_SIZE = 5000
ETL_BATCH_SIZE = 2000

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'etl.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',  # Corrige UnicodeEncodeError según documentación Python
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'etl.api': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.etl': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'ERROR' if not DEBUG else 'DEBUG',
            'propagate': False,
        },
    },
}

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Para desarrollo
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

# ============================================================================
# Celery + Redis/RabbitMQ para ETL asincrónico
# ============================================================================

# Broker configuration (Redis recomendado)
# Redis: redis://localhost:6379/0
# RabbitMQ: amqp://guest:guest@localhost:5672//
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')

# Backend de resultados (donde Celery almacena resultados de tareas)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# Configuración de Celery
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Bogota'  # Zona horaria de Colombia

# Pool de workers
CELERY_WORKER_POOL = 'solo'  # Para desarrollo; usar 'prefork' en producción
CELERY_WORKER_CONCURRENCY = 2  # Número de workers paralelos

# Timeouts y reintentos
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos max por tarea
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos soft limit
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # 60 segundos entre reintentos

# Rutas de tareas (autodiscover)
CELERY_IMPORTS = [
    'apps.etl.tasks',
]

# ============================================================================
# ETL Configuration
# ============================================================================

# Directorio para archivos ETL temporales
ETL_UPLOAD_DIR = os.path.join(BASE_DIR, 'etl_uploads')
os.makedirs(ETL_UPLOAD_DIR, exist_ok=True)

# Validación de archivos ETL
ETL_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ETL_ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.csv']

# Tamaño de batch para carga
ETL_BATCH_SIZE = 1000

# Django file upload settings (según documentación oficial)
# Límite de memoria para request sin archivos (10MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# Límite de campos de formulario (1000 campos)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Tamaño máximo de field name
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB (debe coincidir con ETL_MAX_FILE_SIZE)

# ============================================================================
# Supabase configuration for ETL
# ============================================================================


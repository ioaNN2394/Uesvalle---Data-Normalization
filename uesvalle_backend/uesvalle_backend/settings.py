import os
from dotenv import load_dotenv

load_dotenv()

# settings.py

# settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
        'OPTIONS': {
            # Añade esta opción para deshabilitar explícitamente SSL
            'ssl_mode': 'DISABLED'
        },
    }
}
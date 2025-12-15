# Guía de Configuración para Despliegue

Este documento describe las consideraciones y configuraciones necesarias para desplegar la aplicación en un entorno de producción (Servidor VPS, Nube, etc.), sin atarse a una tecnología específica de hosting.

## Consideraciones Generales

El despliegue requiere orquestar tres servicios principales:
1.  **Servidor Web/Proxy Inverso** (para servir el frontend y proxy al backend).
2.  **Servidor de Aplicación** (para ejecutar el código Python/Django).
3.  **Worker de Tareas** (para ejecutar Celery).

Además de los servicios de infraestructura: Base de Datos (PostgreSQL) y Broker de Mensajes (Redis).

## 1. Configuración del Backend (Producción)

### Variables de Entorno
En el entorno de producción, asegúrate de configurar las siguientes variables (nunca las guardes en el código):

-   `DEBUG`: Debe ser `False`.
-   `SECRET_KEY`: Una cadena larga, aleatoria y segura.
-   `ALLOWED_HOSTS`: Lista de dominios o IPs permitidas (ej. `['mi-dominio.com', 'api.mi-dominio.com']`).
-   `CORS_ALLOWED_ORIGINS`: Lista de orígenes permitidos para peticiones Cross-Origin (ej. `['https://mi-dominio.com']`).
-   Credenciales de Base de Datos (`SUPABASE_DB_*`, `MYSQL_*`).
-   URL de Redis (`CELERY_BROKER_URL`).

### Archivos Estáticos
Django no sirve archivos estáticos de manera eficiente en producción.
1.  Ejecuta `python manage.py collectstatic`. Esto reunirá todos los archivos estáticos en la carpeta definida en `STATIC_ROOT`.
2.  Configura tu servidor web (ej. Nginx) para servir esta carpeta en la URL `/static/`.

### Servidor de Aplicación
No uses `runserver` en producción. Utiliza un servidor WSGI o ASGI robusto.
-   Recomendado: **Gunicorn** o **Uvicorn**.
-   Comando típico: `gunicorn uesvalle_backend.wsgi:application --bind 0.0.0.0:8000`.

### Worker de Celery
El proceso de Celery debe ejecutarse en segundo plano y reiniciarse automáticamente si falla.
-   Se recomienda usar un gestor de procesos como **Supervisor** o **Systemd**.

## 2. Configuración del Frontend (Producción)

### Construcción (Build)
El frontend debe ser compilado a archivos estáticos (HTML, CSS, JS) optimizados.

1.  Ejecuta el comando de construcción:
    ```bash
    npm run build
    ```
2.  Esto generará una carpeta `dist/` (o `build/`) con los archivos listos para producción.

### Servidor Web
Configura tu servidor web para servir el contenido de la carpeta `dist/`.
-   Todas las rutas que no coincidan con un archivo (ej. `/dashboard`, `/users`) deben redirigirse al `index.html` para que el enrutador de Vue (Vue Router) maneje la navegación (SPA Fallback).

## 3. Orquestación (Ejemplo Conceptual)

La arquitectura típica de despliegue se ve así:

-   **Nginx (Puerto 80/443)**:
    -   Ruta `/api/` -> Proxy Pass a `http://localhost:8000` (Gunicorn/Django).
    -   Ruta `/static/` -> Sirve archivos de la carpeta `staticfiles` del backend.
    -   Ruta `/media/` -> Sirve archivos de la carpeta `media` del backend.
    -   Ruta `/` -> Sirve archivos de la carpeta `frontend/dist/`.
        -   Configurar `try_files $uri $uri/ /index.html` para soporte SPA.

## 4. Seguridad

-   Asegúrate de usar **HTTPS** (SSL/TLS) para todas las comunicaciones.
-   La base de datos y Redis no deberían estar expuestos públicamente a internet, solo accesibles por el servidor de aplicación.

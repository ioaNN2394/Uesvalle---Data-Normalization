# Guía de Ejecución Local

Este documento detalla los pasos para configurar y ejecutar el proyecto en un entorno de desarrollo local.

## Prerrequisitos

Asegúrate de tener instalado lo siguiente:

1.  **Python** (v3.10 o superior)
2.  **Node.js** (v18 o superior) y npm/pnpm/yarn.
3.  **Redis** (Necesario para Celery). Debe estar ejecutándose en el puerto 6379 por defecto.
4.  **Git**.

## Configuración del Backend

1.  **Navegar al directorio del backend:**
    ```bash
    cd uesvalle_backend
    ```

2.  **Crear un entorno virtual:**
    ```bash
    python -m venv venv
    ```

3.  **Activar el entorno virtual:**
    -   Windows: `venv\Scripts\activate`
    -   Linux/Mac: `source venv/bin/activate`

4.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configurar variables de entorno:**
    Crea un archivo `.env` en la carpeta `uesvalle_backend/` (al mismo nivel que `manage.py`) con el siguiente contenido base:

    ```env
    DEBUG=True
    SECRET_KEY=tu_clave_secreta_local
    
    # Base de datos PostgreSQL (Supabase o Local)
    SUPABASE_DB_NAME=postgres
    SUPABASE_DB_USER=postgres
    SUPABASE_DB_PASSWORD=tu_password
    SUPABASE_DB_HOST=localhost
    SUPABASE_DB_PORT=5432
    
    # Base de datos MySQL (Fuente de datos)
    MYSQL_DB=source_db
    MYSQL_USER=mysql_user
    MYSQL_PASSWORD=mysql_pass
    MYSQL_HOST=localhost
    MYSQL_PORT=3306
    ```

6.  **Ejecutar migraciones:**
    ```bash
    python manage.py migrate
    ```

7.  **Ejecutar el servidor de desarrollo:**
    ```bash
    python manage.py runserver
    ```
    El backend estará disponible en `http://127.0.0.1:8000`.

8.  **Ejecutar Worker de Celery (para procesamiento ETL):**
    En una nueva terminal (con el entorno virtual activado):
    -   **Windows:**
        ```bash
        celery -A uesvalle_backend worker -l info -P solo
        ```
    -   **Linux/Mac:**
        ```bash
        celery -A uesvalle_backend worker -l info
        ```

## Configuración del Frontend

1.  **Navegar al directorio del frontend:**
    ```bash
    cd frontend
    ```

2.  **Instalar dependencias:**
    ```bash
    npm install
    # O si usas pnpm: pnpm install
    ```

3.  **Ejecutar servidor de desarrollo:**
    ```bash
    npm run dev
    ```
    El frontend estará disponible generalmente en `http://localhost:5173`.

## Verificación

1.  Abre el navegador en la URL del frontend (`http://localhost:5173`).
2.  Intenta realizar una carga de archivo o navegar por la aplicación.
3.  Verifica en la consola del backend que las peticiones se están recibiendo correctamente.

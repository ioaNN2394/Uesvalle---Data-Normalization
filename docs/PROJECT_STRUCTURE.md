# Estructura del Proyecto Uesvalle-Normalization

Este documento describe la composición y organización del proyecto.

## Visión General

El proyecto es una aplicación web moderna diseñada para procesos de ETL (Extracción, Transformación y Carga) y normalización de datos. Está dividido en dos componentes principales:

1.  **Frontend**: Una aplicación de página única (SPA) construida con Vue 3.
2.  **Backend**: Una API RESTful construida con Django y Django Rest Framework.

## Componentes

### Frontend (`/frontend`)
El frontend es responsable de la interfaz de usuario, permitiendo la carga de archivos, visualización de mapas y gestión de reportes.

-   **Framework**: Vue 3 (Composition API)
-   **Build Tool**: Vite
-   **Lenguaje**: TypeScript
-   **Librerías Clave**:
    -   `leaflet` & `vue-leaflet`: Para visualización de mapas.
    -   `axios`: Para comunicación HTTP con el backend.
    -   `lucide-vue-next`: Para iconos.
    -   `vue-router`: Para enrutamiento.

### Backend (`/uesvalle_backend`)
El backend maneja la lógica de negocio, el procesamiento de archivos ETL, la conexión a bases de datos y la autenticación.

-   **Framework**: Django 4.2
-   **API**: Django Rest Framework (DRF)
-   **Lenguaje**: Python
-   **Base de Datos Principal**: PostgreSQL (configurado para Supabase).
-   **Base de Datos Fuente**: MySQL (para extracción de datos).
-   **Procesamiento Asíncrono**: Celery con Redis (para tareas pesadas de ETL).
-   **Librerías Clave**:
    -   `pandas`: Para manipulación y análisis de datos.
    -   `openpyxl` / `xlsxwriter`: Para manejo de Excel.
    -   `reportlab`: Para generación de PDFs.
    -   `structlog`: Para logging estructurado.

## Estructura de Directorios

```text
/
├── frontend/               # Código fuente del Frontend (Vue.js)
│   ├── src/                # Componentes, vistas, servicios
│   ├── public/             # Archivos estáticos públicos
│   ├── package.json        # Dependencias de Node.js
│   └── vite.config.ts      # Configuración de Vite
│
├── uesvalle_backend/       # Código fuente del Backend (Django)
│   ├── apps/               # Aplicaciones Django (módulos de negocio)
│   │   ├── core/           # Funcionalidades núcleo
│   │   └── etl/            # Lógica de ETL
│   ├── uesvalle_backend/   # Configuración del proyecto Django (settings, urls)
│   ├── etl_uploads/        # Directorio temporal para subida de archivos
│   ├── media/              # Archivos generados y subidos por usuarios
│   ├── manage.py           # CLI de Django
│   └── requirements.txt    # Dependencias de Python
│
└── docs/                   # Documentación del proyecto
```

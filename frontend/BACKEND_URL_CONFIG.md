# Configuración de URLs del Backend

## Descripción

Este proyecto utiliza un archivo `.env.local` para configurar la URL del backend de manera centralizada. Esto permite cambiar fácilmente la URL del backend sin modificar el código fuente.

## Configuración

### Archivo `.env.local`

Crea un archivo `.env.local` en la raíz del directorio `frontend/` con el siguiente contenido:

```bash
# Configuración de URLs para el frontend
# En desarrollo: localhost:8000
# En producción: cambiar por la URL real del backend

VITE_BACKEND_URL=http://localhost:8000
```

### Variables de Entorno

- `VITE_BACKEND_URL`: URL completa del backend (incluyendo protocolo y puerto)

## Comportamiento

### Desarrollo
- El proxy de Vite redirige automáticamente las peticiones `/api/*` a la URL configurada
- Las llamadas fetch usan rutas relativas (ej: `/api/etl/upload/`)
- El proxy maneja la redirección transparente

### Producción
- Las llamadas fetch usan URLs completas construidas con `buildApiUrl()`
- Ejemplo: `https://mi-backend.com/api/etl/upload/`

## Uso en Código

### Importación
```typescript
import { API_CONFIG, buildApiUrl, API_HEADERS } from '../../../shared/config/api.config'
```

### Ejemplos de Uso

```typescript
// Para desarrollo (usa rutas relativas)
const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.UPLOAD), {
  method: 'POST',
  body: formData
})

// Para producción (construye URL completa)
const fullUrl = buildApiUrl(API_CONFIG.ENDPOINTS.JOBS) // https://backend.com/api/etl/jobs/
```

## Endpoints Disponibles

```typescript
API_CONFIG.ENDPOINTS = {
  UPLOAD: '/api/etl/upload/',
  JOBS: '/api/etl/jobs/',
  STATUS: '/api/etl/status/',
}
```

## Cambios para Producción

1. Actualiza `.env.local`:
   ```bash
   VITE_BACKEND_URL=https://tu-backend-produccion.com
   ```

2. Reinicia el servidor de desarrollo:
   ```bash
   npm run dev
   ```

3. Para build de producción:
   ```bash
   npm run build
   ```

## Notas Importantes

- El archivo `.env.local` está en `.gitignore` por defecto
- Las variables deben comenzar con `VITE_` para ser accesibles en el cliente
- En producción, asegúrate de que el backend tenga CORS configurado para el dominio del frontend
# 🚀 Guía de Despliegue: Netlify (Frontend) + Render (Backend)

Esta guía te permitirá desplegar tu aplicación con **despliegue automático** cada vez que hagas push a tu repositorio.

## 📋 Arquitectura de Despliegue

```
┌─────────────────┐     ┌──────────────────┐
│   GitHub Repo   │     │                  │
│   (development) │────▶│    Netlify       │ ← Frontend (Vue.js)
│                 │     │                  │
└────────┬────────┘     └──────────────────┘
         │
         │              ┌──────────────────┐
         └─────────────▶│     Render       │ ← Backend (Django)
                        │  + PostgreSQL    │
                        │  + Redis (opt)   │
                        └──────────────────┘
```

---

## 📦 PARTE 1: Configuración del Backend en Render

### Paso 1.1: Crear cuenta en Render

1. Ve a [render.com](https://render.com)
2. Regístrate con tu cuenta de GitHub
3. Autoriza el acceso a tus repositorios

### Paso 1.2: Crear la Base de Datos PostgreSQL (PRIMERO)

1. En el Dashboard, click en **"New +"**
2. Selecciona **"PostgreSQL"**
3. Configura:
   | Campo | Valor |
   |-------|-------|
   | **Name** | `uesvalle-db` |
   | **Region** | Oregon (US West) |
   | **PostgreSQL Version** | 15 |
   | **Plan** | Free |
4. Click en **"Create Database"**
5. **¡IMPORTANTE!** Espera a que se cree y guarda el **Internal Database URL**

### Paso 1.3: Crear el Web Service (Django Backend)

1. Click en **"New +"** → **"Web Service"**
2. Selecciona **"Build and deploy from a Git repository"**
3. Conecta tu repositorio: `ioaNN2394/Uesvalle---Data-Normalization`
4. Configura el servicio:

| Campo | Valor |
|-------|-------|
| **Name** | `uesvalle-backend` |
| **Region** | Oregon (US West) - **misma que la BD** |
| **Branch** | `development` |
| **Root Directory** | `uesvalle_backend` |
| **Runtime** | Python 3 |
| **Build Command** | `./build.sh` |
| **Start Command** | `gunicorn uesvalle_backend.wsgi:application` |
| **Plan** | Free |

### Paso 1.4: Configurar Variables de Entorno en Render

En la sección **"Environment"** del Web Service, agrega:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | (click en "Generate" para generar una) |
| `DEBUG` | `False` |
| `PYTHON_VERSION` | `3.11.6` |
| `DATABASE_URL` | (copia el Internal Database URL de tu PostgreSQL) |
| `CORS_ALLOWED_ORIGINS` | `https://tu-app.netlify.app` (actualizar después) |

### Paso 1.5: Crear Redis + Worker de Celery (OPCIONAL)

Si necesitas procesar tareas asíncronas con Celery:

1. **Crear Key Value (Redis):**
   - Click en **"New +"** → **"Key Value"**
   - Name: `uesvalle-redis`
   - Region: Oregon
   - Plan: Free

2. **Crear Background Worker:**
   - Click en **"New +"** → **"Background Worker"**
   - Conecta el mismo repositorio
   - Configura:

| Campo | Valor |
|-------|-------|
| **Name** | `uesvalle-worker` |
| **Root Directory** | `uesvalle_backend` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `celery -A uesvalle_backend worker -l info` |

3. **Variables de entorno del worker:**
   - `DATABASE_URL`: (misma que el web service)
   - `CELERY_BROKER_URL`: (Internal URL del Redis)
   - `CELERY_RESULT_BACKEND`: (Internal URL del Redis)

---

## 📦 PARTE 2: Configuración del Frontend en Netlify

### Paso 2.1: Crear cuenta en Netlify

1. Ve a [netlify.com](https://netlify.com)
2. Regístrate con tu cuenta de GitHub
3. Autoriza el acceso a tus repositorios

### Paso 2.2: Crear nuevo sitio

1. Click en **"Add new site"** → **"Import an existing project"**
2. Selecciona **GitHub** como proveedor
3. Busca y selecciona: `Uesvalle---Data-Normalization`

### Paso 2.3: Configurar Build Settings

| Campo | Valor |
|-------|-------|
| **Base directory** | `frontend` |
| **Build command** | `pnpm install && pnpm run build` |
| **Publish directory** | `frontend/dist` |

### Paso 2.4: Configurar Variables de Entorno

Ve a **Site configuration** → **Environment variables** y agrega:

| Key | Value |
|-----|-------|
| `VITE_BACKEND_URL` | `https://uesvalle-backend.onrender.com` |
| `NODE_VERSION` | `18` |

> ⚠️ Reemplaza la URL con la URL real de tu servicio en Render

### Paso 2.5: Configurar rama de despliegue

En **Site configuration** → **Build & deploy** → **Branches and deploy contexts**:
- Production branch: `development` (o `main` según prefieras)

---

## 📁 PARTE 3: Archivos de Configuración (YA CREADOS)

Los siguientes archivos ya están en tu proyecto:

### Backend (`uesvalle_backend/`)

| Archivo | Descripción |
|---------|-------------|
| `build.sh` | Script de build para Render |
| `runtime.txt` | Especifica Python 3.11.6 |
| `Procfile` | Comandos de inicio |

### Frontend (`frontend/`)

| Archivo | Descripción |
|---------|-------------|
| `netlify.toml` | Configuración de Netlify |

### Raíz del proyecto

| Archivo | Descripción |
|---------|-------------|
| `render.yaml` | Blueprint para Render (opcional) |

---

## 🚀 PARTE 4: Proceso de Despliegue

### Paso 4.1: Dar permisos de ejecución al script de build

```bash
git update-index --chmod=+x uesvalle_backend/build.sh
```

### Paso 4.2: Hacer commit y push

```bash
git add .
git commit -m "feat: configuración para despliegue en Render y Netlify"
git push origin development
```

### Paso 4.3: Verificar el build en Render

1. Ve a [dashboard.render.com](https://dashboard.render.com)
2. Selecciona tu servicio `uesvalle-backend`
3. Ve a la pestaña **"Events"** y verifica que el build sea exitoso
4. Una vez desplegado, copia la URL (ej: `https://uesvalle-backend.onrender.com`)

### Paso 4.4: Actualizar Netlify con la URL de Render

1. Ve a Netlify → Tu sitio → **Site configuration** → **Environment variables**
2. Actualiza `VITE_BACKEND_URL` con la URL de Render
3. Ve a **Deploys** → **Trigger deploy** → **Deploy site**

### Paso 4.5: Actualizar CORS en Render

1. Ve a Render → `uesvalle-backend` → **Environment**
2. Actualiza `CORS_ALLOWED_ORIGINS` con tu URL de Netlify:
   ```
   https://tu-sitio.netlify.app
   ```
3. El servicio se reiniciará automáticamente

---

## 🔗 PARTE 5: Conectar Todo

### URLs finales (ejemplo)

| Servicio | URL |
|----------|-----|
| **Frontend (Netlify)** | `https://uesvalle-normalization.netlify.app` |
| **Backend (Render)** | `https://uesvalle-backend.onrender.com` |
| **API Base** | `https://uesvalle-backend.onrender.com/api/` |

### Configuración final de variables

**En Render (Backend):**
```env
SECRET_KEY=<generado>
DEBUG=False
DATABASE_URL=<internal-postgres-url>
CORS_ALLOWED_ORIGINS=https://uesvalle-normalization.netlify.app
```

**En Netlify (Frontend):**
```env
VITE_BACKEND_URL=https://uesvalle-backend.onrender.com
NODE_VERSION=18
```

---

## ✅ PARTE 6: Checklist Final

### Backend (Render)
- [ ] PostgreSQL creado y funcionando
- [ ] Web Service desplegado exitosamente
- [ ] Variables de entorno configuradas
- [ ] `DATABASE_URL` conectado a PostgreSQL
- [ ] `CORS_ALLOWED_ORIGINS` con dominio de Netlify
- [ ] Build exitoso (verificar en Events/Logs)

### Frontend (Netlify)
- [ ] Build exitoso
- [ ] `VITE_BACKEND_URL` apunta a Render
- [ ] Redirecciones SPA funcionando (netlify.toml)
- [ ] HTTPS habilitado (automático)

### Conexión
- [ ] Frontend puede hacer requests al Backend
- [ ] Sin errores CORS en consola
- [ ] API respondiendo correctamente

---

## 🔄 Despliegue Automático

Una vez configurado, cada vez que hagas:

```bash
git push origin development
```

Se activará automáticamente:

1. **Render**: Detecta cambios, reconstruye y despliega el backend
2. **Netlify**: Detecta cambios, reconstruye y despliega el frontend

> ⚠️ **Nota sobre Render Free Tier**: Los servicios gratuitos se "duermen" después de 15 minutos de inactividad. La primera request después de dormir tarda ~30 segundos en responder.

---

## 🐛 Troubleshooting

### Error: "Build failed" en Render
```
Solución: Verifica que Root Directory sea "uesvalle_backend"
Verifica que build.sh tenga permisos de ejecución
```

### Error: "Permission denied: ./build.sh"
En tu terminal local, ejecuta:
```bash
git update-index --chmod=+x uesvalle_backend/build.sh
git commit -m "fix: permisos de ejecución para build.sh"
git push origin development
```

### Error: "CORS policy" en el frontend
```
Verifica que CORS_ALLOWED_ORIGINS incluya tu dominio de Netlify
Incluye https:// en la URL
No incluyas / al final de la URL
```

### Error: "502 Bad Gateway" en Render
```
Revisa los logs en Render Dashboard → Events
Verifica que gunicorn esté instalado en requirements.txt
Verifica que el Start Command sea correcto
```

### Error: "Database connection failed"
```
Verifica que DATABASE_URL esté configurado
Usa el Internal Database URL, no el External
Verifica que PostgreSQL esté en la misma región
```

### El sitio tarda mucho en cargar (primera vez)
```
Esto es normal en Render Free Tier
Los servicios se duermen después de 15 min de inactividad
La primera request los "despierta" (~30 seg)
```

---

## 📱 Probar el Despliegue

### 1. Verificar el Backend
```bash
curl https://uesvalle-backend.onrender.com/api/health/
# o visita la URL en el navegador
```

### 2. Verificar el Frontend
Visita tu URL de Netlify y verifica:
- La página carga correctamente
- No hay errores en la consola del navegador
- Las llamadas a la API funcionan

---

## 📞 Recursos Útiles

- [Documentación de Render](https://render.com/docs)
- [Render - Deploy Django](https://render.com/docs/deploy-django)
- [Documentación de Netlify](https://docs.netlify.com/)
- [Django en producción](https://docs.djangoproject.com/en/4.2/howto/deployment/)

---

## 🎉 ¡Listo!

Tu aplicación ahora está desplegada con CI/CD automático. Cada push a `development` actualizará automáticamente ambos servicios.

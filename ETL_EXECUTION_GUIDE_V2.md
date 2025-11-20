# ETL - Guía de Ejecución (Versión Mejorada)

## 📋 Cambios Realizados

### 1. **Nuevo módulo: `data_transformers.py`**
Ubicación: `uesvalle_backend/apps/etl/utils/data_transformers.py`

Funciones clave:
- `limpiar_codigo()`: Convierte valores (float/int/str/None) a códigos DANE limpios
  - Entrada: `123.0` → Salida: `'123'`
  - Entrada: `None` → Salida: `None`
  
- `transformar_maestras_csv()`: Prepara instituciones y sedes desde CSV
  - Entrada: DataFrame con columnas `COD_DANE`, `COD_SEDE_PRINCIPAL`, `NOMBRE_INSTITUCION`
  - Salida: `(df_instituciones, df_sedes, mapa_inst_uuid)`
  - **Garantías**:
    - Limpia códigos DANE
    - Genera UUIDs únicos para padres
    - Mapea hijos a padres correctamente
    - Valida datos no nulos antes de insertar

- `transformar_visitas_mysql()`: Procesa visitas desde MySQL
  - Entrada: `(df_mysql, mapa_sedes_uuid)`
  - Salida: DataFrame limpios para cargar
  - **Arreglos de tipos**:
    - Convierte columnas a string ANTES de tocar valores
    - Reemplaza `.0` en floats convertidos
    - Maneja NaN correctamente

### 2. **Actualización: `orchestrator.py`**

#### a) Nuevos imports
```python
from ..utils.data_transformers import transformar_maestras_csv, transformar_visitas_mysql
```

#### b) Constructor actualizado
Se agregaron atributos:
- `self.mapa_sedes_uuid`: Mapeo dinámico para vincular visitas
- `self.dict_instituciones`: Cache de instituciones por DANE
- `self.dict_sedes`: Cache de sedes por DANE
- `self.dict_instituciones_by_name`: Cache por nombre

#### c) Método `_execute_loading()` reescrito
**Orden de ejecución (CRÍTICO)**:

```
Paso 1: CSV Master (si existe)
├─ 1a: Transformar maestras → (df_inst, df_sedes, mapa)
├─ 1b: Insertar instituciones
├─ 1c: Insertar sedes
└─ 1d: Actualizar mapa_sedes_uuid desde BD

Paso 2: Visitas MySQL (si existe)
├─ 2a: Extraer de MySQL
├─ 2b: Transformar con mapa_sedes_uuid
└─ 2c: Insertar visitas

Paso 3: Matrícula (si existe)

Paso 4: Matrícula Étnica (si existe)
```

#### d) Nuevos métodos de inserción
- `_insert_instituciones(df)`: Carga Instituciones desde DataFrame
- `_insert_sedes(df)`: Carga Sedes desde DataFrame  
- `_get_mapa_sedes_uuid()`: Obtiene mapeo DANE→UUID desde BD
- `_insert_visitas(df)`: Carga Visitas desde DataFrame

---

## 🚀 Cómo Ejecutar

### Opción A: Desde Django Admin
1. Ir a: `admin/etl/etlrun/`
2. Crear un nuevo ETLRun
3. Subir archivos:
   - CSV: `CSV_sedesSISE.csv`
   - (Opcional) Otros archivos de matrícula
4. Guardar y ejecutar

### Opción B: Desde Python (Celery Task)
```python
from apps.etl.tasks import etl_run_job

# Lanza de forma asíncrona
result = etl_run_job.delay(etl_run_id=1)

# Ver resultado después (con polling)
print(result.get())
```

### Opción C: Desde Línea de Comandos
```bash
cd uesvalle_backend

# Ejecutar ETL específico
python manage.py shell
>>> from apps.etl.services.orchestrator import ETLOrchestrator
>>> orchestrator = ETLOrchestrator(etl_run_id=1)
>>> success = orchestrator.execute(dry_run=False)
>>> print(f"✓ ETL completado: {success}")
```

---

## 📊 Validación de Resultados

### 1. Verificar Instituciones
```sql
SELECT COUNT(*) as total, COUNT(DISTINCT dane_ie_id) as unicos
FROM uesvalle.institucion
WHERE dane_ie_id IS NOT NULL;
```
**Esperado**: ~31 instituciones

### 2. Verificar Sedes
```sql
SELECT COUNT(*) as total, COUNT(DISTINCT dane_sede_id) as unicos
FROM uesvalle.sede
WHERE dane_sede_id IS NOT NULL
AND institucion_id IS NOT NULL;
```
**Esperado**: ~56,650 sedes

### 3. Verificar Integridad de Coordinadas
```sql
SELECT COUNT(*) as con_coords, COUNT(*) FILTER (WHERE lat IS NULL OR lon IS NULL) as sin_coords
FROM uesvalle.sede;
```
**Esperado**: Mayoría con coordenadas (lat/lon como números, no strings)

### 4. Verificar Visitas
```sql
SELECT COUNT(*) as total, COUNT(DISTINCT sede_id) as sedes_unicas
FROM uesvalle.visita;
```
**Esperado**: ~4,474 visitas (las que pudieron vincularse a sedes)

### 5. Verificar Metadatos
```sql
SELECT id, nombre, metadata::jsonb -> 'sector' as sector
FROM uesvalle.institucion
LIMIT 3;
```
**Esperado**: Metadata debe contener `sector`, `calendario`, `origen`

---

## 🔍 Solución de Problemas

### ❌ "KeyError: 'COD_DANE'"
**Causa**: Nombres de columnas no normalizados
**Solución**: El código ahora usa `.upper()` en `transformar_maestras_csv()`

### ❌ "0 sedes cargadas"
**Causa anterior**: Uso de `.get()` en pandas Series
**Solución**: Ahora usa indexación directa `row['columna']` con validación

### ❌ "Can only use .str accessor with string values"
**Causa anterior**: Aplicar métodos de string a columnas numéricas
**Solución**: `Normalizer.normalize_all_strings()` antes de procesar

### ❌ "Visitas huérfanas (sin sede vinculada)"
**Causa**: Mapeo DANE incorrecto
**Solución**: Intenta primero por `codigodanesede`, luego por `codigodane`

### ❌ "Error: dane_ie_id IS NULL en instituciones"
**Causa**: Uso de `.0` en códigos
**Solución**: `limpiar_codigo()` reemplaza `123.0` → `'123'`

---

## 📈 Monitoreo de Logs

### Ver logs en tiempo real
```bash
# Terminal 1: Celery Worker
celery -A uesvalle_backend worker -l debug

# Terminal 2: Ver DB logs
tail -f logs/etl.log | grep "✓\|❌\|ERROR"
```

### Logs esperados (ejecución exitosa)
```
--- Iniciando Transformación de Maestras (CSV) ---
Preparando Instituciones...
  ✓ Institución: 123456 - COLEGIO X
Preparando Sedes...
  ✓ Sede: 123456001 -> Institución: 123456
✓ Listas para cargar: 31 Instituciones y 56650 Sedes

--- Iniciando Transformación de Visitas MySQL ---
Convirtiendo columnas a string...
✓ Visitas procesadas: 4474 cargables, 0 huérfanas

✓ Listas para cargar: 31 Instituciones y 56650 Sedes
✓ Instituciones insertadas/actualizadas: 31
✓ Sedes insertadas/actualizadas: 56650
Mapeo de sedes actualizado: 56650 sedes disponibles
✓ Visitas insertadas: 4474, 0 fallidas
```

---

## ⚙️ Configuración Requerida

Asegúrate que en `settings.py` exista:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'uesvalle',
        # ... configuración BD principal (Supabase)
    },
    'source_mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'database_name',
        'USER': 'username',
        'PASSWORD': 'password',
        'HOST': 'host',
        'PORT': '3306',
    }
}

DATABASES_ROUTERS = ['apps.core.db_routers.ETLRouter']
```

---

## ✅ Checklist Pre-Ejecución

- [ ] Archivo CSV (`CSV_sedesSISE.csv`) está disponible
- [ ] MySQL source_mysql está configurado y accesible
- [ ] Supabase (BD principal) está disponible
- [ ] Celery worker está corriendo (si usas async)
- [ ] Logs están configurados (app/etl_uploads/logs/)
- [ ] BD está limpia (sin conflictos de DANE previos)

```bash
# Limpiar datos de test anteriores
python manage.py shell
>>> from apps.etl.models import *
>>> ETLRun.objects.filter(status='failed').delete()
>>> Institucion.objects.filter(dane_ie_id__isnull=True).delete()  # Borra instituciones mal cargadas
```

---

## 📚 Referencias

- **CSV Parser**: `apps/etl/utils/csv_parser.py`
- **Normalizer**: `apps/etl/utils/normalizer.py`
- **Data Transformers**: `apps/etl/utils/data_transformers.py` (**NUEVO**)
- **Orchestrator**: `apps/etl/services/orchestrator.py` (**ACTUALIZADO**)
- **Models**: `apps/etl/models.py`
- **Tasks**: `apps/etl/tasks.py`


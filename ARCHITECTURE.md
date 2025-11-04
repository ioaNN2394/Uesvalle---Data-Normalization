# ETL Architecture - Technical Deep Dive

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Vue 3 Frontend                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ETL Upload Module                                        │   │
│  │ • ETLUploadModal (orchestrator)                         │   │
│  │ • UploadDropzone (drag & drop)                          │   │
│  │ • FileQueueItem (progress tracking)                     │   │
│  │ • ConfirmationDialog (user confirmation)                │   │
│  │ • useETLUpload (composable)                             │   │
│  │ • etlUploadService (validation + upload)                │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬─────────────────────────────────────────────────┘
                 │ HTTP POST /api/etl/jobs/
                 │ [file_ids, dry_run, cancel_on_error]
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Django REST Backend                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ API Layer (views_v2.py)                                 │   │
│  │ • ETLJobViewSet (CRUD + actions)                        │   │
│  │   - POST /jobs/ → create() → enqueue Celery            │   │
│  │   - GET  /jobs/:id/ → retrieve()                       │   │
│  │   - POST /jobs/:id/cancel/ → cancel()                  │   │
│  │   - GET  /jobs/:id/logs/?level=error&page=1            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                         │
│  ┌──────────────────────▼──────────────────────────────────┐   │
│  │ Task Orchestration (tasks.py)                           │   │
│  │ • etl_run_job(etl_run_id) @shared_task                 │   │
│  │   - Llamado asincronamente por Celery                  │   │
│  │   - Delegada a ETLOrchestrator.execute()               │   │
│  │ • etl_cancel_job(etl_run_id) @shared_task              │   │
│  │ • etl_cleanup_expired_files() @periodic_task           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                         │
│  ┌──────────────────────▼──────────────────────────────────┐   │
│  │ Orchestrator (orchestrator.py)                          │   │
│  │ Coordina todo el pipeline ETL                           │   │
│  │                                                          │   │
│  │ ┌───────────────────────────────────────────────────┐   │   │
│  │ │ Phase 1: EXTRACTION                              │   │   │
│  │ │ • ExcelExtractor.extract() → ExtractionResult   │   │   │
│  │ │ • MySQLExtractor.extract() → ExtractionResult   │   │   │
│  │ │ • MultiSourceExtractor.extract_and_merge()      │   │   │
│  │ └─────────────────────────┬───────────────────────┘   │   │
│  │                           ▼                             │   │
│  │ ┌───────────────────────────────────────────────────┐   │   │
│  │ │ Phase 2: TRANSFORMATION                           │   │   │
│  │ │ • BasicTransformer.transform()                    │   │   │
│  │ │   - Map columns                                   │   │   │
│  │ │   - Clean data (nulls, trim)                      │   │   │
│  │ │   - Normalize (uppercase, etc)                    │   │   │
│  │ │   - Validate (rules engine)                       │   │   │
│  │ │   - Add hashes (SHA-256 per row)                  │   │   │
│  │ │ • InstitutionTransformer (specialized)            │   │   │
│  │ │ • ChangeDetector.detect_changes()                 │   │   │
│  │ │   - Compara nuevos vs existentes                  │   │   │
│  │ │   - Retorna (new_df, updated_df)                  │   │   │
│  │ └─────────────────────────┬───────────────────────┘   │   │
│  │                           ▼                             │   │
│  │ ┌───────────────────────────────────────────────────┐   │   │
│  │ │ Phase 3: LOADING                                 │   │   │
│  │ │ • PostgreSQLLoader.load()                        │   │   │
│  │ │   - INSERT ... ON CONFLICT                       │   │   │
│  │ │   - Transacción atómica                          │   │   │
│  │ │   - Batch processing (1000 registros)            │   │   │
│  │ │   - Retry logic                                  │   │   │
│  │ │ • SupabaseLoader (alternativa)                   │   │   │
│  │ └─────────────────────────┬───────────────────────┘   │   │
│  │                           ▼                             │   │
│  │ ┌───────────────────────────────────────────────────┐   │   │
│  │ │ Phase 4: AUDITING                                │   │   │
│  │ │ • Registra ETLError (errors por fase)            │   │   │
│  │ │ • Registra ChangeLog (auditoría de cambios)     │   │   │
│  │ │ • Crea ETLMetrics (performance)                  │   │   │
│  │ │ • Ejecuta DataQualityCheck                       │   │   │
│  │ └───────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Service Layer (services/)                               │   │
│  │ • DataExtractor (ABC) ← MySQLExtractor, ExcelExtractor │   │
│  │ • DataTransformer (ABC) ← BasicTransformer, Custom     │   │
│  │ • DataLoader (ABC) ← PostgreSQLLoader, SupabaseLoader  │   │
│  │ • Utilities: HashGenerator, ColumnMapper, ValidationRules │ │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Data Models (models.py)                                 │   │
│  │ • ETLRun (ejecución)                                    │   │
│  │ • ETLFile (archivo subido)                              │   │
│  │ • ETLError (errores)                                    │   │
│  │ • ChangeLog (auditoría)                                 │   │
│  │ • DataQualityCheck (checks)                             │   │
│  │ • ETLMetrics (métricas)                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────┬────────────────────┘
                 │                            │
    ┌────────────▼─────┐        ┌─────────────▼──────────┐
    │    Redis Cache   │        │   Message Broker       │
    │  (RESULT_BACKEND)│        │   (Celery)            │
    │ • Tasks results  │        │ • Queue: celery       │
    │ • Cache data     │        │ • Queue: etl          │
    └──────────────────┘        └──────────┬─────────────┘
                                           │ Enqueue/Dequeue
    ┌────────────────────────────────────┐ │
    │      Celery Worker Pool             │ │
    │  (concurrency=2, prefork)           │◄┘
    │  • Poll queue every Nth sec         │
    │  • Execute task                     │
    │  • Report result to Redis           │
    │  • Retry on failure (max 3)         │
    └────────────────────────────────────┘
                                           │
            ┌──────────────────────────────▼──────────────────┐
            │           Data Persistence Layer                │
            │  ┌──────────────┐    ┌─────────────────────┐   │
            │  │ Supabase     │    │ MySQL Legacy       │   │
            │  │ (PostgreSQL) │    │ (Source System)    │   │
            │  │              │    │                     │   │
            │  │ Tables:      │    │ Tables:            │   │
            │  │ • fact_*     │    │ • catalogo_*       │   │
            │  │ • dim_*      │    │ • institucion      │   │
            │  │              │    │ • sede             │   │
            │  └──────────────┘    └─────────────────────┘   │
            └──────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### 1. User Upload Flow

```
Frontend UI
    │
    ├─ Select files (Excel)
    ├─ Validate (size, extension, MIME)
    ├─ Show queue with progress
    ├─ POST /api/etl/jobs/ {file_ids, dry_run, cancel_on_error}
    │
    ▼
Backend API
    │
    ├─ Create ETLRun (status='pending')
    ├─ Link files to ETLRun
    ├─ Queue task: etl_run_job.delay(etl_run_id)
    │
    ▼
Celery Worker
    │
    ├─ Dequeue task from Redis
    ├─ Call ETLOrchestrator.execute()
    │
    ▼
ETL Pipeline
    │
    ├─ Extract: Read files + validate structure
    ├─ Transform: Normalize, validate, hash rows
    ├─ Load: Upsert to Supabase with ON CONFLICT
    ├─ Audit: Log changes, metrics, quality checks
    │
    ▼
Database
    │
    ├─ Supabase: INSERT/UPDATE fact_institucion
    ├─ Django: Store in ETLRun, ETLError, ChangeLog
    │
    ▼
Frontend
    │
    └─ Poll /api/etl/jobs/:id/ for status updates
```

---

## 📦 Service Layer Design

### Base Classes (Abstract)

```python
class DataExtractor(ABC):
    """Template method pattern"""
    @abstractmethod
    def extract(self, **kwargs) -> ExtractionResult:
        """Subclases implementan: MySQLExtractor, ExcelExtractor"""
        pass

class DataTransformer(ABC):
    """Strategy pattern para transformación"""
    @abstractmethod
    def transform(self, df, **kwargs) -> TransformationResult:
        """Subclases: BasicTransformer, InstitutionTransformer"""
        pass

class DataLoader(ABC):
    """Adapter pattern para diferentes BD"""
    @abstractmethod
    def load(self, df, table_name, **kwargs) -> LoadingResult:
        """Subclases: PostgreSQLLoader, SupabaseLoader"""
        pass
```

### Composition

```python
class ETLOrchestrator:
    """Orchestrator pattern - compone servicios"""
    
    def execute(self):
        # 1. Extraer
        extractor = MySQLExtractor()
        extraction_result = extractor.extract(...)
        
        # 2. Transformar
        transformer = InstitutionTransformer()
        transformation_result = transformer.transform(extraction_result.data)
        
        # 3. Cargar
        loader = PostgreSQLLoader()
        loading_result = loader.load(transformation_result.data, ...)
        
        # 4. Auditar
        self._audit(loading_result)
```

---

## 🔐 Validation Rules Engine

```python
# Reglas predefinidas
validation_rules = {
    'codigo_dane': [
        lambda s: ValidationRules.is_not_null(s),
        lambda s: ValidationRules.is_unique(s),
        lambda s: ValidationRules.matches_pattern(s, r'^\d{11}$')
    ],
    'estado': [
        lambda s: ValidationRules.is_in_set(s, {'activo', 'inactivo'})
    ]
}

# Aplicación
valid_mask = True
for column, rules in validation_rules.items():
    for rule in rules:
        is_valid, invalid_idx = rule(df[column])
        valid_mask = valid_mask & is_valid
```

---

## #️⃣ Hashing Strategy (Change Detection)

```python
# Para cada fila:
row = {
    'codigo_dane': '108001001001',
    'nombre': 'COLEGIO CENTRAL',
    'estado': 'activo',
    'created_at': '2024-01-01T10:00:00'
}

# Excluyendo timestamp
hash_input = json.dumps({
    'codigo_dane': '108001001001',
    'nombre': 'COLEGIO CENTRAL',
    'estado': 'activo'
}, sort_keys=True)

# hash = SHA-256(hash_input)
hash_value = 'abc123def456...'

# Comparación
if hash_value == existing_hash:
    # Sin cambios → UPDATE si otros campos cambiaron
else:
    # Cambió → UPSERT
```

---

## 🤖 Celery Task Execution

### Task Lifecycle

```
┌─────────────────────────────────────────────────┐
│ 1. RECEIVED                                     │
│    • Tarea encolada en Redis                    │
│    • Estado: PENDING                            │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ 2. STARTED                                      │
│    • Worker dequeued la tarea                   │
│    • Estado: STARTED                            │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ 3. PROGRESS (Custom)                            │
│    • @bind self.update_state()                  │
│    • Estado: PROGRESS con meta={'stage': '...'}│
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ 4. SUCCESS or RETRY                             │
│    • Si error y retries < max: RETRY            │
│    • Si éxito: SUCCESS                          │
│    • Result guardado en Redis                   │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ 5. COMPLETE                                     │
│    • Frontend poll obtiene resultado            │
│    • UI actualiza                               │
└─────────────────────────────────────────────────┘
```

### Retry Strategy

```python
@shared_task(bind=True, max_retries=3)
def etl_run_job(self, etl_run_id, ...):
    try:
        # Lógica del job
        orchestrator.execute()
    except Exception as e:
        # Retry con backoff exponencial
        # countdown = 60 * (attempt + 1)
        # attempt 0: 60s
        # attempt 1: 120s
        # attempt 2: 180s
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
```

---

## 📊 Data Quality Checks

```python
# Validaciones ejecutadas en fase TRANSFORM

checks = [
    # Completeness
    {'column': 'codigo_dane', 'rule': 'not_null', 'threshold': 100},
    
    # Consistency
    {'column': 'estado', 'rule': 'in_set', 'values': {'activo', 'inactivo'}},
    
    # Format
    {'column': 'email', 'rule': 'pattern', 'pattern': r'^[\w\.-]+@[\w\.-]+\.\w+$'},
    
    # Range
    {'column': 'year', 'rule': 'in_range', 'min': 2000, 'max': 2024},
]

# Resultado
quality_check = DataQualityCheck(
    check_type='completeness',
    status='pass' if valid_count == total else 'fail',
    records_checked=total,
    records_failed=invalid_count,
    success_rate=valid_count / total * 100
)
```

---

## 🔀 ON CONFLICT Strategy (Upsert)

### PostgreSQL SQL

```sql
INSERT INTO fact_institucion 
  (codigo_dane, nombre, estado, direccion, telefono, email, ...)
VALUES 
  (%s, %s, %s, %s, %s, %s, ...),
  (%s, %s, %s, %s, %s, %s, ...),
  ...
ON CONFLICT (codigo_dane) 
DO UPDATE SET 
  nombre = EXCLUDED.nombre,
  estado = EXCLUDED.estado,
  direccion = EXCLUDED.direccion,
  telefono = EXCLUDED.telefono,
  email = EXCLUDED.email,
  updated_at = NOW()
WHERE fact_institucion.updated_hash != EXCLUDED.updated_hash;
```

### Ventajas

- ✅ **Idempotencia**: ejecutar 10 veces = mismo resultado
- ✅ **Atomicidad**: todo o nada por transacción
- ✅ **Performance**: 1 round-trip a BD
- ✅ **Cambios detectados**: via hash comparison

---

## 🧠 Memory Management

### Extractores

```python
# NO: Cargar todo a memoria
df = read_csv('/massive/file.csv')  # 1GB+ en RAM

# SÍ: Chunk processing
for chunk in read_csv('/file.csv', chunksize=10000):
    # Procesar 10K filas a la vez
    transform_batch(chunk)
```

### Transformadores

```python
# NO: Múltiples copias
df_clean = df.copy()  # +500MB
df_normalized = df_clean.copy()  # +500MB

# SÍ: In-place operations
df.dropna(inplace=True)  # Modifica en lugar
df = df[df['codigo'].str.len() == 11]  # Filtro
```

---

## 🔍 Logging Strategy

```python
# Estructura jerárquica
LOGGING = {
    'loggers': {
        'etl': {'level': 'INFO'},                    # Raíz
        'etl.extraction': {'level': 'DEBUG'},        # Detallado
        'etl.transformation': {'level': 'DEBUG'},    # Detallado
        'etl.loading': {'level': 'INFO'},            # Standard
        'etl.orchestrator': {'level': 'INFO'},       # Standard
    }
}

# Uso
logger = logging.getLogger('etl.extraction')
logger.info(f"Extrayendo {file_path}...")
logger.debug(f"Detected {col_count} columns")
logger.error(f"Failed to parse: {error}", exc_info=True)
```

---

## 🎯 Error Handling

```python
try:
    # Fase EXTRACT
    extraction_result = extractor.extract(...)
except ExtractionError as e:
    logger.error(f"Extraction failed: {e}")
    ETLError.objects.create(
        phase='extraction',
        error_type=type(e).__name__,
        message=str(e)
    )
    if cancel_on_error:
        return False
    else:
        continue  # Siguiente archivo

try:
    # Fase TRANSFORM
    transformation_result = transformer.transform(df)
except TransformationError as e:
    logger.error(f"Transformation failed: {e}")
    # Registrar pero continuar (registrar rows inválidas)

try:
    # Fase LOAD
    loading_result = loader.load(df, table_name)
except LoadingError as e:
    # Reintentar a nivel de registros individuales
    for _, row in df.iterrows():
        try:
            loader.load(pd.DataFrame([row]), ...)
        except Exception as row_error:
            ETLError.objects.create(...)
```

---

## 🔐 Security Considerations

### API Authentication

```python
# Frontend debe enviar token
class ETLJobViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]  # Para desarrollo
    # En producción: [IsAuthenticated]
```

### Service Role Key

```python
# NUNCA exponer SUPABASE_SERVICE_ROLE_KEY en frontend
# Solo en backend

# Usar RLS (Row Level Security) en Supabase si es posible
# CREATE POLICY para controlar acceso
```

### File Validation

```python
# Validar en backend (frontend puede ser bypasseado)
ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}
MAX_FILE_SIZE = 50 * 1024 * 1024

# Check 1: Extensión
if not file_path.endswith(tuple(ALLOWED_EXTENSIONS)):
    raise ValueError("Invalid extension")

# Check 2: MIME type
mime_type, _ = mimetypes.guess_type(file_path)
if mime_type not in ['application/vnd.ms-excel', 
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
    raise ValueError("Invalid MIME type")

# Check 3: Tamaño
if os.path.getsize(file_path) > MAX_FILE_SIZE:
    raise ValueError("File too large")

# Check 4: Contenido (parse como Excel)
try:
    df = pd.read_excel(file_path)
    if df.empty:
        raise ValueError("Excel vacío")
except Exception as e:
    raise ValueError(f"Invalid Excel: {e}")
```

---

## 📈 Performance Optimization

### Indexes (Supabase/PostgreSQL)

```sql
-- Para búsquedas rápidas
CREATE INDEX idx_fact_institucion_codigo_dane 
  ON fact_institucion(codigo_dane);

-- Para cambios detectados
CREATE INDEX idx_fact_institucion_hash 
  ON fact_institucion(updated_hash);

-- Para auditoría
CREATE INDEX idx_changelog_etl_run_id 
  ON changelog(etl_run_id);
```

### Connection Pooling

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # 10 min
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

### Batch Operations

```python
# NO: Hacer 1000 INSERT individuales
for row in df.iterrows():
    Model.objects.create(**row)

# SÍ: bulk_create
objects = [Model(**row) for row in df.iterrows()]
Model.objects.bulk_create(objects, batch_size=1000)
```

---

## 🧪 Testing Strategy

### Unit Tests

```python
# test_extractors.py
def test_excel_extractor_valid_file():
    extractor = ExcelExtractor()
    result = extractor.extract('test.xlsx')
    assert result.record_count > 0
    assert isinstance(result.data, pd.DataFrame)

# test_transformers.py
def test_institution_transformer():
    df = pd.DataFrame({
        'codigo_dane': ['108001001001'],
        'nombre': ['TEST COLLEGE']
    })
    transformer = InstitutionTransformer()
    result = transformer.transform(df)
    assert len(result.data) == 1
    assert result.errors == []
```

### Integration Tests

```python
# test_orchestrator.py
def test_etl_full_pipeline(test_db, test_excel_file):
    etl_run = ETLRun.objects.create(status='pending')
    ETLFile.objects.create(
        etl_run=etl_run,
        file_path=test_excel_file
    )
    
    orch = ETLOrchestrator(etl_run.id)
    success = orch.execute(dry_run=True)
    
    assert success == True
    assert etl_run.status == 'completed'
```

### E2E Tests

```bash
# Usando pytest + factoryboy
pytest tests/e2e/test_etl_complete.py -v
```


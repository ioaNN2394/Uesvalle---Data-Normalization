/**
 * ETL FRONTEND-BACKEND INTEGRATION IMPLEMENTATION SUMMARY
 * ======================================================
 * 
 * Documento de referencia para la implementación completa del flujo ETL
 * que conecta el Frontend (Vue 3 + TypeScript) con el Backend (Django + DRF).
 * 
 * FECHA: Noviembre 4, 2025
 * OBJETIVO: Conectar Front y Back para el flujo ETL completo
 * 
 * FLUJO IMPLEMENTADO:
 * ==================
 * 
 * 1. FRONTEND - Componente ETLUploadModal
 *    - Usuario selecciona archivos Excel (.xlsx, .xls)
 *    - Los archivos se validan localmente (tamaño, tipo)
 *    - Se muestran en la cola de carga
 *    
 * 2. FRONTEND - Upload a Backend
 *    POST /api/etl/upload/
 *    - FormData multipart/form-data con el campo 'file'
 *    - Respuesta JSON con lista de archivos cargados + IDs
 *    
 * 3. FRONTEND - Crear Job ETL
 *    POST /api/etl/jobs/
 *    - Body: { file_ids: [...], dry_run: false, cancel_on_error: true }
 *    - Respuesta: { id: ..., status: "queued", task_id: "..." }
 *    
 * 4. BACKEND - Procesamiento Asincrónico (Celery)
 *    etl_run_job.delay()
 *    - Extrae datos de archivos Excel
 *    - Transforma y valida datos
 *    - Carga en Supabase (cuando esté implementado)
 *    
 * 5. FRONTEND - Polling de Status
 *    GET /api/etl/status/
 *    - Obtiene estado general del sistema ETL
 *    - Permite mostrar widget de estado en dashboard
 * 
 * ARCHIVOS MODIFICADOS:
 * ====================
 * 
 * BACKEND:
 * --------
 * 
 * apps/etl/views_v2.py
 *   - Agregado endpoint @api_view(['POST']) upload_etl_file()
 *   - Valida extensión, tamaño, MIME type
 *   - Guarda archivo en etl_uploads/
 *   - Crea registro ETLFile con status='pending'
 *   - Responde con lista de archivos cargados y IDs
 *   
 * apps/etl/urls.py
 *   - Agregado path('upload/', upload_etl_file)
 *   - Rutas disponibles:
 *     * POST /api/etl/upload/
 *     * POST /api/etl/jobs/
 *     * GET /api/etl/jobs/
 *     * GET /api/etl/jobs/:id/
 *     * POST /api/etl/jobs/:id/cancel/
 *     * GET /api/etl/status/
 *   
 * apps/etl/models.py
 *   - ETLRun: Agregados status 'pending', 'queued', 'completed'
 *   - ETLFile: Agregada relación ForeignKey a ETLRun via 'files'
 *   
 * apps/etl/serializers.py
 *   - Agregado ETLFileSerializer con campos de estado y progreso
 *   
 * apps/etl/services/orchestrator.py
 *   - Reescrito completamente (versión simplificada funcional)
 *   - Extract: Lee archivos Excel con pandas
 *   - Transform: Limpia datos, elimina filas vacías
 *   - Load: Marca archivos como procesados
 *   - Manejo de errores por archivo
 *   
 * apps/etl/tasks.py
 *   - etl_run_job: Crea orchestrator y ejecuta pipeline
 *   - etl_cancel_job: Marca job como cancelled
 *   - etl_cleanup_expired_files: Limpia archivos temporales
 *   
 * uesvalle_backend/settings.py
 *   - REST_FRAMEWORK: Agregados MultiPartParser, FormParser
 *   - CORS_ALLOWED_ORIGINS: Incluye localhost:5173 (Vite)
 *   - LOGGING: Logger 'etl.api' configurado
 *   - ETL_UPLOAD_DIR: Directorio para archivos temporales
 *   - FILE_UPLOAD_MAX_MEMORY_SIZE: Límite de carga
 *   - DATA_UPLOAD_MAX_MEMORY_SIZE: Límite de memory
 *   - Celery: Redis broker y result backend
 *   
 * FRONTEND:
 * ---------
 * 
 * src/modules/etl/components/ETLUploadModal.vue
 *   - Actualizado uploadFile() para usar fetch real en /api/etl/upload/
 *   - Agregado createETLJob() para crear job con file_ids
 *   - Agregado evento 'job-created' en emit
 *   - Guarda serverFileId en queuedFile para referenciarlo
 *   - Flujo: upload files → create job → emit job-created
 *   
 * src/modules/etl/services/etlUploadService.ts
 *   - Ya estaba bien configurado
 *   - uploadFile() usa fetch con FormData
 *   - Endpoint por defecto: /api/etl/upload
 *   
 * src/modules/etl/composables/useETLUpload.ts
 *   - Ya estaba bien implementado
 *   - Maneja cola de archivos
 *   - Cálculo de progreso global
 *   
 * CARACTERISTICAS IMPLEMENTADAS:
 * =============================
 * 
 * ✓ Validación de archivos (extensión, tamaño, MIME)
 * ✓ Upload multipart/form-data
 * ✓ Guardado seguro con hash SHA-256 en el nombre
 * ✓ Logging detallado en logs/etl.log
 * ✓ Relación ETLFile ↔ ETLRun
 * ✓ Procesamiento asincrónico con Celery
 * ✓ Extracción de datos de Excel con pandas
 * ✓ Transformación básica (limpieza, validación)
 * ✓ Estados de jobs (pending, queued, running, completed, failed, cancelled)
 * ✓ CORS configurado para frontend
 * ✓ Manejo de errores con respuestas JSON estructuradas
 * ✓ Directorios creados: etl_uploads/, logs/
 * ✓ Migraciones generadas para los modelos
 * 
 * CARACTERISTICAS PENDIENTES:
 * ===========================
 * 
 * ⊘ Load completo a Supabase (existe estructura pero no persistence real)
 * ⊘ Quality checks avanzados
 * ⊘ ETLError, ETLMetrics, ChangeLog, DataQualityCheck (modelos opcionales)
 * ⊘ Celery Beat schedule para limpieza automática
 * ⊘ WebSocket para notificaciones en tiempo real
 * ⊘ Bulk operations con upsert en Supabase
 * 
 * PRUEBA DEL SISTEMA:
 * ===================
 * 
 * 1. Backend:
 *    python manage.py migrate
 *    python manage.py runserver
 *    
 * 2. Frontend:
 *    npm run dev
 *    
 * 3. Celery (opcional para tests):
 *    celery -A uesvalle_backend worker -l info
 *    
 * 4. Abrir DevTools en http://localhost:5173
 *    - Network: Verificar POST /api/etl/upload/
 *    - Network: Verificar POST /api/etl/jobs/
 *    - Console: Sin errores CORS
 *    
 * 5. Logs:
 *    tail -f uesvalle_backend/logs/etl.log
 *    
 * ESTRUCTURA DE RESPUESTAS:
 * =========================
 * 
 * POST /api/etl/upload/ (200 OK)
 * {
 *   "uploaded": [
 *     {
 *       "id": 1,
 *       "filename": "instituciones.xlsx",
 *       "file_type": "excel",
 *       "file_size": 102400,
 *       "status": "pending",
 *       "uploaded_at": "2024-01-15T10:00:00Z"
 *     }
 *   ],
 *   "failed": 0
 * }
 * 
 * POST /api/etl/jobs/ (202 Accepted)
 * {
 *   "id": 1,
 *   "status": "queued",
 *   "started_at": "2024-01-15T10:00:00Z",
 *   "finished_at": null,
 *   "meta": {"task_id": "celery-uuid-..."}
 * }
 * 
 * GET /api/etl/status/ (200 OK)
 * {
 *   "total_jobs": 1,
 *   "running_jobs": 1,
 *   "success_jobs": 0,
 *   "failed_jobs": 0,
 *   "success_rate": 0.0,
 *   "last_job": {
 *     "id": 1,
 *     "status": "running",
 *     "started_at": "2024-01-15T10:00:00Z"
 *   }
 * }
 * 
 * PRÓXIMOS PASOS:
 * ===============
 * 
 * 1. Completar Load a Supabase
 *    - Usar bulk_create/bulk_update de Django
 *    - Implementar upsert con unique_key
 *    
 * 2. Agregar WebSocket para notificaciones
 *    - Django Channels para updates en tiempo real
 *    
 * 3. Implementar Quality Checks
 *    - Validaciones de negocio más avanzadas
 *    
 * 4. Agregar ETLError, ETLMetrics modelos (opcionales)
 *    - Para tracking detallado de errors
 *    
 * 5. Documentación de API
 *    - Swagger/OpenAPI con drf-spectacular
 *    
 * CONTACTO/NOTAS:
 * ================
 * 
 * Este documento resume toda la implementación del flujo ETL.
 * El código está bien comentado y los archivos tienen docstrings.
 * 
 * Los logs detallados están en: uesvalle_backend/logs/etl.log
 * Para DEBUG, activar DEBUG=True en .env
 */

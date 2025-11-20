# Arquitectura de Comunicación del ETL: Frontend y Backend

Este documento detalla el flujo de comunicación entre el frontend (Vue.js) y el backend (Django) para el proceso de Extracción, Transformación y Carga (ETL), desde que el usuario sube un archivo hasta que el backend lo procesa.

## Resumen del Flujo

El proceso se divide en dos etapas principales:

1.  **Carga de Archivos**: El usuario selecciona uno o más archivos Excel (`.xlsx`, `.xls`) en la interfaz. El frontend sube cada archivo de forma individual al backend. El backend guarda estos archivos en el servidor y crea un registro en la base de datos para cada uno, devolviendo un identificador único por archivo.
2.  **Creación del Job ETL**: Una vez que todos los archivos han sido subidos, el frontend envía una segunda petición al backend para iniciar el proceso ETL. Esta petición incluye los identificadores de los archivos que se deben procesar. El backend entonces encola una tarea asíncrona para que procese los datos sin bloquear la respuesta al cliente.

![Diagrama de Flujo del ETL](https://i.imgur.com/rO4g3f2.png)

---

## 1. Carga de Archivos (File Upload)

Esta fase se encarga de transferir los archivos desde el cliente al servidor de forma segura y eficiente.

### Frontend (Cliente)

-   **Componente Principal**: `ETLUploadModal.vue`
-   **Lógica de Carga**: `useETLUpload.ts` y `etlUploadService.ts`

**Pasos:**

1.  **Selección de Archivos**: El usuario interactúa con el componente `UploadDropzone.vue` (dentro de `ETLUploadModal.vue`) para seleccionar archivos de su equipo.
2.  **Validación en el Cliente**: Antes de la subida, el composable `useETLUpload.ts` utiliza el servicio `etlUploadService.ts` para realizar validaciones básicas:
    -   **Extensión del archivo**: Solo se permiten `.xlsx` y `.xls`.
    -   **Tamaño del archivo**: Se limita a un máximo de 50MB.
    -   **Tipo MIME**: Se verifica que el tipo de archivo corresponda a un documento de Excel.
3.  **Subida Individual**: Cada archivo validado se sube mediante una petición `POST` al endpoint `/api/etl/upload/`. Se utiliza `FormData` para enviar el archivo.
    ```typescript
    // En ETLUploadModal.vue
    const formData = new FormData();
    formData.append('file', queuedFile.file);

    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.UPLOAD), {
      method: 'POST',
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    });
    ```
4.  **Recepción de ID**: El backend responde con un objeto JSON que contiene los detalles del archivo guardado, incluyendo un `id` único de la base de datos. El frontend almacena este `id` para usarlo en la siguiente fase.
    ```typescript
    // En ETLUploadModal.vue
    const data = await response.json();
    if (data.uploaded && data.uploaded.length > 0) {
      // Guardar el ID del archivo para usarlo luego al crear el job
      (queuedFile as any).serverFileId = data.uploaded[0].id;
    }
    ```

### Backend (Servidor)

-   **URL Endpoint**: `/api/etl/upload/`
-   **Vista**: `upload_etl_file` en `uesvalle_backend/apps/etl/views_v2.py`

**Pasos:**

1.  **Recepción de la Petición**: La vista `upload_etl_file` recibe la petición `POST` con el archivo.
2.  **Validación en el Servidor**: Se realizan validaciones de seguridad:
    -   Extensión del archivo.
    -   Tamaño máximo del archivo.
3.  **Almacenamiento Físico**:
    -   Se genera un nombre de archivo único utilizando un hash MD5 para evitar colisiones y ofuscar el nombre original.
    -   El archivo se guarda en el directorio `etl_uploads/` en el sistema de archivos del servidor.
    ```python
    # En uesvalle_backend/apps/etl/views_v2.py
    upload_dir = getattr(settings, 'ETL_UPLOAD_DIR', os.path.join(settings.BASE_DIR, 'etl_uploads'))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_hash = hashlib.md5(f"{file_obj.name}{timezone.now().isoformat()}".encode()).hexdigest()
    unique_filename = f"{file_hash}_{file_obj.name}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    ```
4.  **Creación del Registro en la BD**: Se crea una instancia del modelo `ETLFile` en la base de datos. Este registro contiene metadatos sobre el archivo, como su nombre original, la ruta en el servidor (`file_path`), el tamaño y su estado inicial (`pending`).
5.  **Respuesta al Frontend**: La vista serializa el objeto `ETLFile` recién creado y lo devuelve en la respuesta JSON con un código de estado `200 OK`.

---

## 2. Creación del Job ETL

Una vez que el frontend ha subido todos los archivos deseados, inicia el proceso principal del ETL.

### Frontend (Cliente)

-   **Componente**: `ETLUploadModal.vue`

**Pasos:**

1.  **Inicio del Procesamiento**: El usuario hace clic en el botón "Iniciar procesamiento".
2.  **Recopilación de IDs**: El frontend recopila todos los `serverFileId` que obtuvo durante la fase de carga.
3.  **Petición de Creación de Job**: Se envía una única petición `POST` al endpoint `/api/etl/jobs/`. El cuerpo de la petición contiene un array con los IDs de los archivos.
    ```typescript
    // En ETLUploadModal.vue
    const fileIds = fileQueue.value
      .filter(f => f.status === 'completed')
      .map(f => (f as any).serverFileId);

    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.JOBS), {
      method: 'POST',
      headers: { ... },
      body: JSON.stringify({
        file_ids: fileIds,
        dry_run: false,
        cancel_on_error: true
      })
    });
    ```
4.  **Confirmación**: El backend responde con un `202 Accepted`, indicando que la tarea ha sido recibida y se procesará en segundo plano. El frontend puede usar esta información para mostrar un estado de "procesando" al usuario.

### Backend (Servidor)

-   **URL Endpoint**: `/api/etl/jobs/`
-   **Vista**: `ETLJobViewSet` (método `create`) en `uesvalle_backend/apps/etl/views_v2.py`
-   **Procesamiento Asíncrono**: Celery y `ETLOrchestrator`

**Pasos:**

1.  **Recepción de la Petición**: El método `create` del `ETLJobViewSet` recibe la lista de `file_ids`.
2.  **Creación del `ETLRun`**:
    -   Se crea una instancia del modelo `ETLRun`, que representa la ejecución completa del job ETL.
    -   Se asocian los `ETLFile` (correspondientes a los `file_ids` recibidos) a este `ETLRun`.
3.  **Encolado de la Tarea Asíncrona**:
    -   En lugar de procesar los datos directamente en la vista (lo que bloquearía la respuesta), se encola una tarea de Celery (`etl_run_job.delay`).
    -   Esto permite que el servidor responda inmediatamente al frontend mientras el trabajo pesado se realiza en segundo plano.
    ```python
    # En uesvalle_backend/apps/etl/views_v2.py
    task = etl_run_job.delay(
        etl_run_id=etl_run.id,
        dry_run=dry_run,
        cancel_on_error=cancel_on_error
    )
    etl_run.metadata['task_id'] = task.id
    etl_run.status = 'queued'
    etl_run.save()
    ```
4.  **Orquestación del ETL (`ETLOrchestrator`)**:
    -   El worker de Celery ejecuta la tarea, que a su vez llama al `ETLOrchestrator`.
    -   **Extract**: El orquestador lee los archivos Excel desde la ruta (`file_path`) almacenada en la base de datos utilizando la librería `pandas`.
    -   **Transform**: Realiza la limpieza y normalización de los datos en memoria.
    -   **Load**: Prepara los datos para ser cargados en la base de datos de destino. **Nota importante**: El código actual tiene un marcador de posición para la carga a Supabase, pero la lógica de inserción final no está implementada. El proceso actual solo simula la carga.

## Interacción con Supabase

En el código analizado, **no hay una interacción directa con Supabase para el almacenamiento de archivos**. Los archivos subidos se guardan en el sistema de archivos local del servidor backend.

La única mención a Supabase se encuentra en un comentario dentro del `ETLOrchestrator`, sugiriendo que la base de datos de destino para los datos transformados es (o será) Supabase.

```python
# En uesvalle_backend/apps/etl/services/orchestrator.py
def _execute_loading(self, dry_run: bool = False) -> bool:
    """Fase LOAD: persistir datos transformados."""
    try:
        logger.info(f"Cargando datos a Supabase ({'DRY RUN' if dry_run else 'LIVE'})...")
        
        # ...
        
        if not dry_run:
            # En producción, aquí iría la lógica de carga a Supabase
            # Por ahora, solo registramos que se cargó
            logger.info(f"[LOAD] {len(df_valid)} registros cargados de {filename}")
```

Por lo tanto, el flujo actual **no sube los archivos a Supabase Storage**. Los archivos residen en el servidor que ejecuta la aplicación Django.

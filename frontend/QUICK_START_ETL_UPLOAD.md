# 🚀 Guía de Uso - Módulo de Carga ETL

## Inicio Rápido

### 1. El módulo ya está integrado en el Sidebar

El botón de "Actualización ETL" (icono de subida ⬆️) aparece en la barra lateral inferior junto a "Notificaciones" y "Reportes".

**No requiere configuración adicional** - simplemente funciona.

---

## Uso del Componente

### Opción A: Uso Directo (como en Sidebar)

```vue
<script setup lang="ts">
import { ref } from 'vue'
import ETLUploadModal from '@/modules/etl/components/ETLUploadModal.vue'

const showETLModal = ref(false)

const handleOpen = () => {
  showETLModal.value = true
}

const handleClose = () => {
  showETLModal.value = false
}
</script>

<template>
  <div>
    <button @click="handleOpen">Abrir Carga ETL</button>
    
    <ETLUploadModal 
      :is-open="showETLModal" 
      @close="handleClose"
    />
  </div>
</template>
```

### Opción B: Uso del Composable (recomendado para lógica compleja)

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useETLUpload } from '@/modules/etl/composables/useETLUpload'

const showModal = ref(false)

const {
  fileQueue,
  isProcessing,
  canStartProcessing,
  completedFilesCount,
  addFiles,
  removeFile,
  startProcessing,
  reset
} = useETLUpload({
  maxFileSize: 50 * 1024 * 1024,
  endpoint: '/api/etl/upload',
  onProgress: (idx, progress) => {
    console.log(`Archivo ${idx}: ${progress}%`)
  },
  onFileComplete: (idx, success) => {
    console.log(`Archivo ${idx}: ${success ? 'OK' : 'Error'}`)
  }
})

const handleFilesSelected = (files: File[]) => {
  const result = addFiles(Array.from(files))
  console.log(`Agregados: ${result.successful}`)
}

const handleStart = async () => {
  const stats = await startProcessing()
  console.log(`Completados: ${stats.completed}, Fallidos: ${stats.failed}`)
}

const handleClose = () => {
  reset()
  showModal.value = false
}
</script>

<template>
  <div>
    <button @click="showModal = true">Abrir ETL</button>
    
    <div v-if="showModal" class="modal">
      <h2>Cargar Archivos</h2>
      
      <p>Archivos: {{ fileQueue.length }}</p>
      
      <button 
        @click="handleStart" 
        :disabled="!canStartProcessing || isProcessing"
      >
        {{ isProcessing ? 'Procesando...' : 'Iniciar' }}
      </button>
      
      <button @click="handleClose">Cerrar</button>
    </div>
  </div>
</template>
```

---

## Servicio de Validación

### Validar un archivo

```typescript
import { validateETLFile } from '@/modules/etl/services/etlUploadService'

const file = document.getElementById('fileInput').files[0]
const result = validateETLFile(file, {
  maxFileSize: 100 * 1024 * 1024, // 100MB
  allowedExtensions: ['.xlsx', '.xls', '.csv']
})

if (!result.valid) {
  console.error('Archivo no válido:', result.error)
} else {
  console.log('Archivo válido ✓')
}
```

### Cargar un archivo

```typescript
import { uploadFile } from '@/modules/etl/services/etlUploadService'

const controller = new AbortController()

const result = await uploadFile(
  file,
  { endpoint: '/api/etl/upload' },
  (progress) => console.log(`Progreso: ${progress}%`),
  controller.signal
)

if (result.success) {
  console.log('Cargado exitosamente', result.data)
} else {
  console.error('Error:', result.message)
}

// Cancelar carga en cualquier momento
controller.abort()
```

### Cargar múltiples archivos

```typescript
import { uploadFilesParallel } from '@/modules/etl/services/etlUploadService'

const files = Array.from(document.getElementById('fileInput').files || [])
const stats = await uploadFilesParallel(
  files,
  { maxParallelUploads: 3 },
  (fileIdx, progress) => {
    console.log(`Archivo ${fileIdx}: ${progress}%`)
  },
  (fileIdx, success) => {
    console.log(`Archivo ${fileIdx}: ${success ? 'OK' : 'ERROR'}`)
  }
)

console.log(`Completados: ${stats.completed}, Errores: ${stats.failed}`)
```

---

## Personalización

### Cambiar endpoint

**En ETLUploadModal.vue:**

```typescript
const uploadFile = async (queuedFile: QueuedFile) => {
  const formData = new FormData()
  formData.append('file', queuedFile.file)
  
  // Usa tu endpoint personalizado
  const response = await fetch('/tu/endpoint/personalizado', {
    method: 'POST',
    body: formData
  })
  
  // ...
}
```

### Cambiar límite de tamaño

```typescript
// En el servicio
const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100MB

// O al usar
const result = validateETLFile(file, {
  maxFileSize: 200 * 1024 * 1024 // 200MB
})
```

### Cambiar extensiones permitidas

```typescript
const result = validateETLFile(file, {
  allowedExtensions: ['.xlsx', '.xls', '.csv']
})
```

### Cambiar máximo de cargas paralelas

```typescript
const stats = await uploadFilesParallel(
  files,
  { maxParallelUploads: 5 } // En lugar de 3
)
```

---

## Eventos y Callbacks

### Progreso de carga

```typescript
const { fileQueue } = useETLUpload({
  onProgress: (fileIndex, progress) => {
    // fileIndex: índice del archivo en la cola
    // progress: 0-100
    console.log(`Archivo ${fileIndex}: ${progress}%`)
  }
})
```

### Finalización de archivo

```typescript
const { fileQueue } = useETLUpload({
  onFileComplete: (fileIndex, success) => {
    if (success) {
      console.log(`Archivo ${fileIndex} completado ✓`)
    } else {
      console.log(`Archivo ${fileIndex} falló ✗`)
    }
  }
})
```

### Cambios en cola

```typescript
const { fileQueue } = useETLUpload({
  onQueueChange: (queue) => {
    console.log(`Cola actualizada: ${queue.length} archivos`)
  }
})
```

---

## Manejo de Errores

### Archivos inválidos

Los errores se muestran en la interfaz de forma clara:

```
Archivo "datos.pdf" - Estado: Error
Error: Formato no permitido: solo .xlsx o .xls
[Botón: Reintentar] [Botón: Quitar]
```

### Errores de red

Si hay problema de conexión:

```
Archivo "datos.xlsx" - Estado: Error
Error: Error de red
[Botón: Reintentar] [Botón: Quitar]
```

### Errores del servidor

Si el servidor devuelve error 500:

```
Archivo "datos.xlsx" - Estado: Error
Error: Error del servidor: 500
[Botón: Reintentar] [Botón: Quitar]
```

---

## Accesibilidad

### Navegación por teclado

| Tecla | Acción |
|-------|--------|
| **Tab** | Navega hacia el siguiente elemento |
| **Shift+Tab** | Navega hacia el elemento anterior |
| **Enter** | Activa botones, abre selector de archivos |
| **Espacio** | Activa botones, abre dropzone |
| **ESC** | Cierra modal (si es seguro) |

### Lectores de pantalla

El modal anuncia:
- ✅ Título y descripción
- ✅ Estados de archivos
- ✅ Progreso (%)
- ✅ Errores
- ✅ Cambios importantes

---

## Ejemplos Prácticos

### Ejemplo 1: Carga simple

```vue
<script setup lang="ts">
import { ref } from 'vue'
import ETLUploadModal from '@/modules/etl/components/ETLUploadModal.vue'

const showModal = ref(false)
</script>

<template>
  <button @click="showModal = true" class="btn-etl">
    📊 Actualizar ETL
  </button>
  
  <ETLUploadModal :is-open="showModal" @close="showModal = false" />
</template>
```

### Ejemplo 2: Con notificaciones

```vue
<script setup lang="ts">
import { useETLUpload } from '@/modules/etl/composables/useETLUpload'

const { startProcessing, reset, fileQueue } = useETLUpload({
  onFileComplete: (idx, success) => {
    if (success) {
      showNotification(`Archivo procesado correctamente`, 'success')
    } else {
      showNotification(`Error al procesar archivo`, 'error')
    }
  }
})

const handleProcess = async () => {
  const stats = await startProcessing()
  showNotification(
    `${stats.completed} completados, ${stats.failed} con error`,
    'info'
  )
}

const showNotification = (msg: string, type: string) => {
  // Tu lógica de notificaciones
  console.log(`[${type.toUpperCase()}] ${msg}`)
}
</script>
```

### Ejemplo 3: Con validación previa

```vue
<script setup lang="ts">
import { validateETLFile } from '@/modules/etl/services/etlUploadService'

const handleDropFiles = async (files: File[]) => {
  const validFiles: File[] = []
  const errors: string[] = []

  for (const file of files) {
    const result = validateETLFile(file)
    if (result.valid) {
      validFiles.push(file)
    } else {
      errors.push(`${file.name}: ${result.error}`)
    }
  }

  if (errors.length > 0) {
    console.error('Archivos inválidos:', errors)
    showDialog('Algunos archivos no se pueden cargar', errors.join('\n'))
  }

  if (validFiles.length > 0) {
    // Proceder con carga
    addValidFiles(validFiles)
  }
}
</script>
```

---

## Troubleshooting

### ¿El modal no aparece?

```typescript
// Asegúrate de que:
// 1. showETLModal es reactivo
const showETLModal = ref(false) ✓

// 2. El binding es correcto
<ETLUploadModal :is-open="showETLModal" @close="..." /> ✓

// 3. El componente está importado
import ETLUploadModal from '@/modules/etl/components/ETLUploadModal.vue' ✓
```

### ¿Los archivos no se cargan?

```typescript
// 1. Verifica el endpoint
// DevTools > Network > POST request

// 2. Verifica los headers
// Content-Type debe ser multipart/form-data (automático)

// 3. Verifica el servidor
console.log('Respuesta del servidor:', response)
```

### ¿El progreso no se actualiza?

```typescript
// Asegúrate de que el servidor envía eventos de progreso
// O usa XMLHttpRequest.upload.addEventListener('progress', ...)

// Alternativa: progreso simulado (actual)
setTimeout(() => {
  queuedFile.progress = 100
  // Actualiza lista
}, 2000)
```

---

## Referencias Rápidas

- **Documentación:** `ETL_UPLOAD_DOCUMENTATION.md`
- **Tipos TypeScript:** `types/etl.types.ts`
- **Servicio:** `services/etlUploadService.ts`
- **Composable:** `composables/useETLUpload.ts`

---

**¿Preguntas?** Consulta la documentación completa o contacta al equipo.

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="modal-overlay"
      @click.self="handleOverlayClick"
      :inert="isProcessing"
    >
      <div
        class="etl-upload-modal"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="headerId"
        :aria-describedby="descriptionId"
      >
        <!-- Modal Header -->
        <div class="modal-header">
          <div class="modal-header-content">
            <h2 :id="headerId" class="modal-title">Subir archivos para actualizar ETL</h2>
            <p :id="descriptionId" class="modal-subtitle">
              Archivos soportados: .xlsx, .xls, .csv. Puedes arrastrar y soltar o seleccionarlos desde tu equipo.
            </p>
          </div>
          <button
            class="modal-close-btn"
            @click="handleCloseClick"
            :disabled="isProcessing"
            aria-label="Cerrar diálogo"
            title="Cerrar (ESC)"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <!-- Dropzone -->
        <UploadDropzone
          @files-selected="handleFilesSelected"
          :disabled="isProcessing"
        />

        <!-- File Queue -->
        <div v-if="fileQueue.length > 0" class="file-queue-section">
          <h3 class="section-title">
            Archivos en cola ({{ fileQueue.length }})
          </h3>
          <div class="file-queue-container" role="list">
            <FileQueueItem
              v-for="(file, index) in fileQueue"
              :key="file.id"
              :file="file"
              :index="index"
              @remove="removeFile"
              @retry="retryFile"
              :disabled="isProcessing"
              role="listitem"
            />
          </div>
        </div>

        <!-- Processing Progress (Global) -->
        <div v-if="isProcessing" class="global-progress-section">
          <div class="progress-info">
            <span class="progress-label">Procesando archivos...</span>
            <span class="progress-percentage">{{ globalProgressPercentage }}%</span>
          </div>
          <div
            class="progress-bar"
            role="progressbar"
            :aria-valuenow="globalProgressPercentage"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="`Progreso general: ${globalProgressPercentage}%`"
          >
            <div
              class="progress-fill"
              :style="{ width: `${globalProgressPercentage}%` }"
            ></div>
          </div>
        </div>

        <!-- Processing Summary -->
        <div v-if="processingComplete" class="processing-summary">
          <div class="summary-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <div class="summary-content">
            <h3 class="summary-title">Procesamiento completado</h3>
            <p class="summary-message">
              Se procesaron {{ completedFilesCount }} {{ completedFilesCount === 1 ? 'archivo' : 'archivos' }} correctamente.
              Los datos fueron enviados al ETL.
            </p>
          </div>
        </div>

        <!-- Modal Actions -->
        <div class="modal-actions">
          <button
            v-if="!processingComplete && !isProcessing"
            class="btn btn-secondary"
            @click="handleCloseClick"
            aria-label="Cancelar la carga"
          >
            Cancelar
          </button>
          <button
            v-else-if="processingComplete"
            class="btn btn-secondary"
            @click="closeModal"
            aria-label="Cerrar el diálogo"
          >
            Cerrar
          </button>

          <button
            v-if="!processingComplete && !isProcessing"
            class="btn btn-primary"
            @click="handleStartProcessing"
            :disabled="!canStartProcessing"
            aria-label="Iniciar procesamiento de archivos"
          >
            Iniciar procesamiento
          </button>
          <button
            v-else-if="isProcessing"
            class="btn btn-danger"
            @click="handleStopProcessing"
            aria-label="Detener el procesamiento"
          >
            Detener
          </button>
        </div>
      </div>

      <!-- Confirmation Dialog -->
      <ConfirmationDialog
        v-if="showConfirmation"
        title="Cancelar carga y procesamiento"
        :message="confirmationMessage"
        confirm-label="Sí, cancelar"
        cancel-label="Volver"
        is-destructive
        @confirm="confirmCancel"
        @cancel="cancelConfirmation"
      />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import UploadDropzone from './UploadDropzone.vue'
import FileQueueItem from './FileQueueItem.vue'
import ConfirmationDialog from './ConfirmationDialog.vue'
import { API_CONFIG, buildApiUrl, API_HEADERS } from '../../../shared/config/api.config'

interface QueuedFile {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'completed' | 'error'
  progress: number
  error?: string
  abortController?: AbortController
}

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits<{
  close: []
  'job-created': [jobData: any]
}>()

const headerId = 'etl-modal-title'
const descriptionId = 'etl-modal-description'

const fileQueue = ref<QueuedFile[]>([])
const isProcessing = ref(false)
const processingComplete = ref(false)
const showConfirmation = ref(false)
const globalProgressPercentage = ref(0)
const completedFilesCount = ref(0)
const activeUploads = ref(new Map<string, AbortController>())
const focusedElement = ref<HTMLElement | null>(null)

// Límites
const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB
const MAX_PARALLEL_UPLOADS = 3
const ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.csv']
const ALLOWED_MIME_TYPES = [
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-excel',
  'text/csv',
  'application/csv',
  'application/x-csv'
]

const confirmationMessage = ref('Si cancelas la operación los archivos que subiste se borrarán y deberás cargarlos nuevamente')

const canStartProcessing = computed(() => {
  return fileQueue.value.length > 0 && fileQueue.value.some(f => f.status === 'pending')
})

const handleFilesSelected = (files: File[]) => {
  for (const file of files) {
    addFileToQueue(file)
  }
}

const addFileToQueue = (file: File) => {
  // Validaciones
  const validationError = validateFile(file)
  if (validationError) {
    // Añadir archivo con error
    const id = generateId()
    fileQueue.value.push({
      id,
      file,
      status: 'error',
      progress: 0,
      error: validationError
    })
    announceForScreenReaders(`Error: ${validationError}`)
    return
  }

  // Verificar duplicados
  const isDuplicate = fileQueue.value.some(f => f.file.name === file.name)
  if (isDuplicate) {
    announceForScreenReaders(`Error: El archivo ${file.name} ya está en la cola`)
    return
  }

  // Agregar archivo válido
  const id = generateId()
  fileQueue.value.push({
    id,
    file,
    status: 'pending',
    progress: 0,
    abortController: new AbortController()
  })
  announceForScreenReaders(`Archivo ${file.name} agregado a la cola`)
}

const validateFile = (file: File): string | null => {
  // Validar extensión
  const fileName = file.name.toLowerCase()
  const hasValidExtension = ALLOWED_EXTENSIONS.some(ext => fileName.endsWith(ext))

  if (!hasValidExtension) {
    return `Formato no permitido: solo .xlsx, .xls o .csv. Recibido: ${file.type || 'desconocido'}`
  }

  // Validar MIME type (algunos navegadores reportan text/csv como tipo MIME para .csv)
  if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) {
    return `Tipo MIME no permitido. Acepta: ${ALLOWED_MIME_TYPES.join(', ')}`
  }

  // Validar tamaño
  if (file.size > MAX_FILE_SIZE) {
    return `Archivo demasiado grande. Máximo: ${MAX_FILE_SIZE / 1024 / 1024}MB. Tu archivo: ${(file.size / 1024 / 1024).toFixed(2)}MB`
  }

  return null
}

const removeFile = (fileId: string) => {
  const index = fileQueue.value.findIndex(f => f.id === fileId)
  if (index > -1) {
    const file = fileQueue.value[index]
    // Cancelar si está subiendo
    if (file.abortController) {
      file.abortController.abort()
    }
    fileQueue.value.splice(index, 1)
    announceForScreenReaders(`Archivo eliminado de la cola`)
  }
}

const retryFile = (fileId: string) => {
  const file = fileQueue.value.find(f => f.id === fileId)
  if (file) {
    file.status = 'pending'
    file.progress = 0
    file.error = undefined
    file.abortController = new AbortController()
    announceForScreenReaders(`Reintentando archivo ${file.file.name}`)
  }
}

const handleStartProcessing = async () => {
  isProcessing.value = true
  processingComplete.value = false
  completedFilesCount.value = 0

  // Procesar archivos en paralelo (máx 3)
  const pendingFiles = fileQueue.value.filter(f => f.status === 'pending')

  for (let i = 0; i < pendingFiles.length; i += MAX_PARALLEL_UPLOADS) {
    const batch = pendingFiles.slice(i, i + MAX_PARALLEL_UPLOADS)
    await Promise.all(batch.map(f => uploadFile(f)))
  }

  // Calcular resumen
  completedFilesCount.value = fileQueue.value.filter(f => f.status === 'completed').length
  
  // Si hay archivos completados, crear el job ETL
  if (completedFilesCount.value > 0) {
    await createETLJob()
  }
  
  isProcessing.value = false
  processingComplete.value = true
  announceForScreenReaders(`Procesamiento completado. ${completedFilesCount.value} archivos procesados correctamente.`)
}

const createETLJob = async () => {
  try {
    announceForScreenReaders('Creando job de ETL...')
    
    // Recolectar IDs de archivos completados
    const fileIds = fileQueue.value
      .filter(f => f.status === 'completed')
      .map(f => (f as any).serverFileId)
      .filter(id => id)
    
    if (fileIds.length === 0) {
      announceForScreenReaders('No hay archivos válidos para procesar')
      return
    }
    
    // Enviar solicitud para crear job
    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.JOBS), {
      method: 'POST',
      headers: {
        ...API_HEADERS,
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({
        file_ids: fileIds,
        dry_run: false,
        cancel_on_error: true
      })
    })
    
    if (!response.ok) {
      throw new Error(`Error creando job: ${response.status}`)
    }
    
    const jobData = await response.json()
    announceForScreenReaders(`Job ETL creado exitosamente. ID: ${jobData.id}`)
    
    // Emitir evento con los datos del job
    emit('job-created', jobData)
    
  } catch (error) {
    const errorMsg = (error as Error).message || 'Error desconocido'
    announceForScreenReaders(`Error creando job: ${errorMsg}`)
    console.error('Error creating ETL job:', error)
  }
}

const uploadFile = async (queuedFile: QueuedFile) => {
  try {
    queuedFile.status = 'uploading'
    const formData = new FormData()
    formData.append('file', queuedFile.file)

    // Usar fetch para subir archivo al backend
    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.UPLOAD), {
      method: 'POST',
      body: formData,
      // No establecer Content-Type para que el navegador lo haga automáticamente con boundary
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    })

    if (!response.ok) {
      throw new Error(`Error del servidor: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    
    // Verificar que el upload fue exitoso
    if (data.uploaded && data.uploaded.length > 0) {
      queuedFile.status = 'completed'
      queuedFile.progress = 100
      // Guardar el ID del archivo para usarlo luego al crear el job
      ;(queuedFile as any).serverFileId = data.uploaded[0].id
      updateGlobalProgress()
      announceForScreenReaders(`Archivo ${queuedFile.file.name} subido exitosamente`)
    } else {
      throw new Error(data.error || 'Error al subir archivo')
    }
  } catch (error) {
    queuedFile.status = 'error'
    queuedFile.error = (error as Error).message || 'Error desconocido'
    updateGlobalProgress()
    announceForScreenReaders(`Error al procesar ${queuedFile.file.name}: ${queuedFile.error}`)
  }
}

const updateGlobalProgress = () => {
  const total = fileQueue.value.length
  if (total === 0) {
    globalProgressPercentage.value = 0
    return
  }
  const completed = fileQueue.value.reduce((sum, f) => sum + f.progress, 0)
  globalProgressPercentage.value = Math.round(completed / total)
}

const handleStopProcessing = () => {
  // Cancelar todas las cargas activas
  activeUploads.value.forEach(controller => controller.abort())
  activeUploads.value.clear()

  // Marcar archivos en progreso como cancelados
  fileQueue.value.forEach(f => {
    if (f.status === 'uploading') {
      f.status = 'pending'
      f.progress = 0
    }
  })

  isProcessing.value = false
  announceForScreenReaders('Procesamiento detenido')
}

const handleOverlayClick = () => {
  if (!isProcessing) {
    handleCloseClick()
  }
}

const handleCloseClick = () => {
  if (fileQueue.value.length > 0 && !processingComplete.value) {
    showConfirmation.value = true
  } else {
    closeModal()
  }
}

const confirmCancel = () => {
  showConfirmation.value = false
  fileQueue.value = []
  closeModal()
}

const cancelConfirmation = () => {
  showConfirmation.value = false
}

const closeModal = () => {
  fileQueue.value = []
  isProcessing.value = false
  processingComplete.value = false
  globalProgressPercentage.value = 0
  showConfirmation.value = false
  emit('close')

  // Devolver foco al trigger
  if (focusedElement.value) {
    focusedElement.value.focus()
  }
}

// Accesibilidad: gestionar foco y ESC
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && !isProcessing.value && !processingComplete.value) {
    handleCloseClick()
  }
}

const announceForScreenReaders = (message: string) => {
  const announcement = document.createElement('div')
  announcement.setAttribute('role', 'status')
  announcement.setAttribute('aria-live', 'polite')
  announcement.setAttribute('aria-atomic', 'true')
  announcement.className = 'sr-only'
  announcement.textContent = message
  document.body.appendChild(announcement)
  setTimeout(() => announcement.remove(), 1000)
}

const generateId = () => `file-${Date.now()}-${Math.random()}`

onMounted(() => {
  focusedElement.value = document.activeElement as HTMLElement
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})

watch(
  () => props.isOpen,
  (newVal) => {
    if (!newVal) {
      closeModal()
    }
  }
)
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.2);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(2px);
}

.etl-upload-modal {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  padding: 32px;
  width: 100%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.modal-header-content {
  flex: 1;
}

.modal-title {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 8px 0;
}

.modal-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
}

.modal-close-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #6b7280;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.modal-close-btn:hover:not(:disabled) {
  background: #f3f4f6;
  color: #111827;
}

.modal-close-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Sections */
.file-queue-section,
.global-progress-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.file-queue-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}

/* Progress */
.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.progress-label {
  color: #374151;
  font-weight: 500;
}

.progress-percentage {
  color: #6b7280;
  font-weight: 600;
}

.progress-bar {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3498db, #2980b9);
  border-radius: 3px;
  transition: width 0.3s ease;
}

/* Processing Summary */
.processing-summary {
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 16px;
  background: #f0fdf4;
  border-radius: 8px;
  border-left: 4px solid #22c55e;
}

.summary-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #22c55e;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.summary-content {
  flex: 1;
}

.summary-title {
  font-size: 14px;
  font-weight: 600;
  color: #166534;
  margin: 0 0 4px 0;
}

.summary-message {
  font-size: 14px;
  color: #166534;
  margin: 0;
  line-height: 1.4;
}

/* Actions */
.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.btn {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
}

.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-secondary {
  background: transparent;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

/* Screen reader only text */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Scroll bar styling */
.file-queue-container::-webkit-scrollbar {
  width: 6px;
}

.file-queue-container::-webkit-scrollbar-track {
  background: #f3f4f6;
  border-radius: 3px;
}

.file-queue-container::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.file-queue-container::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* Responsive */
@media (max-width: 768px) {
  .etl-upload-modal {
    padding: 24px;
    max-width: 95vw;
  }

  .modal-title {
    font-size: 20px;
  }

  .modal-actions {
    flex-direction: column-reverse;
  }

  .btn {
    width: 100%;
  }
}
</style>

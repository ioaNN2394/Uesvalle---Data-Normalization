<template>
  <div
    class="dropzone-container"
    @drop.prevent="handleDrop"
    @dragover.prevent="isDragOver = true"
    @dragleave.prevent="isDragOver = false"
    @dragenter.prevent="isDragOver = true"
    :class="{ 'is-drag-over': isDragOver, 'is-disabled': disabled }"
    role="region"
    aria-label="Zona para subir archivos de Excel"
  >
    <div class="dropzone-content">
      <div class="dropzone-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
      </div>

      <div class="dropzone-text">
        <p class="dropzone-main-text">Arrastra tus Excel aquí o haz clic para seleccionarlos</p>
        <p class="dropzone-sub-text">
          Formatos: .xlsx, .xls | Máximo: {{ (maxFileSize / 1024 / 1024).toFixed(0) }}MB por archivo
        </p>
      </div>

      <button
        class="dropzone-button"
        @click="triggerFileInput"
        :disabled="disabled"
        aria-label="Seleccionar archivos de Excel"
      >
        Seleccionar archivos
      </button>

      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
        @change="handleFileInputChange"
        class="file-input"
        aria-hidden="true"
        tabindex="-1"
      />
    </div>

    <!-- Validation Message -->
    <div v-if="validationMessage" class="validation-message" role="alert" aria-live="polite">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      {{ validationMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  },
  maxFileSize: {
    type: Number,
    default: 50 * 1024 * 1024 // 50MB
  }
})

const emit = defineEmits<{
  filesSelected: [files: File[]]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)
const validationMessage = ref('')

const ALLOWED_EXTENSIONS = ['.xlsx', '.xls']

const triggerFileInput = () => {
  if (!props.disabled && fileInput.value) {
    fileInput.value.click()
  }
}

const validateFile = (file: File): boolean => {
  const fileName = file.name.toLowerCase()
  const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) => fileName.endsWith(ext))

  if (!hasValidExtension) {
    return false
  }

  // Validar tamaño
  if (file.size > props.maxFileSize) {
    return false
  }

  return true
}

const handleDrop = (event: DragEvent) => {
  if (props.disabled) return

  isDragOver.value = false
  validationMessage.value = ''

  const files = event.dataTransfer?.files
  if (!files || files.length === 0) return

  const validFiles = Array.from(files).filter((file) => {
    const isValid = validateFile(file)
    if (!isValid) {
      validationMessage.value = `Archivo no válido: ${file.name}. Solo se permiten .xlsx y .xls`
      return false
    }
    return true
  })

  if (validFiles.length > 0) {
    emit('filesSelected', validFiles)
    validationMessage.value = ''
  }
}

const handleFileInputChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (files && files.length > 0) {
    const filesArray = Array.from(files)
    emit('filesSelected', filesArray)
    // Reset input
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}
</script>

<style scoped>
.dropzone-container {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 40px 24px;
  background: #f9fafb;
  transition: all 0.3s ease;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dropzone-container:hover:not(.is-disabled) {
  border-color: #a5b4fc;
  background: #f3f4f6;
  box-shadow: 0 0 0 3px rgba(165, 180, 252, 0.1);
}

.dropzone-container:focus-within:not(.is-disabled) {
  outline: 2px solid #3498db;
  outline-offset: 2px;
}

.dropzone-container.is-drag-over:not(.is-disabled) {
  border-color: #3498db;
  background: #eff6ff;
  box-shadow: 0 0 0 4px rgba(52, 152, 219, 0.1);
  transform: scale(1.01);
}

.dropzone-container.is-disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: #f3f4f6;
}

.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
}

.dropzone-icon {
  color: #a5b4fc;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-4px);
  }
}

.dropzone-text {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dropzone-main-text {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.dropzone-sub-text {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

.dropzone-button {
  padding: 10px 20px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropzone-button:hover:not(:disabled) {
  background: #2980b9;
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
}

.dropzone-button:active:not(:disabled) {
  transform: scale(0.98);
}

.dropzone-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dropzone-button:focus-visible {
  outline: 2px solid #3498db;
  outline-offset: 2px;
}

.file-input {
  display: none;
}

/* Validation Message */
.validation-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #991b1b;
  font-size: 13px;
  margin: -8px 0 0 0;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.validation-message svg {
  flex-shrink: 0;
  color: #dc2626;
}

/* Responsive */
@media (max-width: 768px) {
  .dropzone-container {
    padding: 24px 16px;
  }

  .dropzone-main-text {
    font-size: 14px;
  }

  .dropzone-sub-text {
    font-size: 12px;
  }

  .dropzone-icon {
    width: 36px;
    height: 36px;
  }

  .dropzone-icon svg {
    width: 36px;
    height: 36px;
  }
}
</style>

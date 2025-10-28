/**
 * useETLUpload Composable
 * Hook reutilizable para la lógica de carga de ETL
 * Ideal si necesitas usar esta funcionalidad en múltiples lugares
 */

import { ref, computed } from 'vue'
import type { Ref } from 'vue'
import {
  validateETLFile,
  uploadFilesParallel,
  generateFileId
} from '../services/etlUploadService'
import type {
  QueuedFile,
  UploadOptions
} from '../types/etl.types'

export interface UseETLUploadOptions extends UploadOptions {
  onProgress?: (fileIndex: number, progress: number) => void
  onFileComplete?: (fileIndex: number, success: boolean) => void
  onQueueChange?: (queue: QueuedFile[]) => void
}

export function useETLUpload(options: UseETLUploadOptions = {}) {
  // Estado
  const fileQueue: Ref<QueuedFile[]> = ref([])
  const isProcessing = ref(false)
  const processingComplete = ref(false)
  const globalProgress = ref(0)
  const activeUploads = new Map<string, AbortController>()

  // Computed
  const completedFilesCount = computed(
    () => fileQueue.value.filter(f => f.status === 'completed').length
  )

  const failedFilesCount = computed(
    () => fileQueue.value.filter(f => f.status === 'error').length
  )

  const canStartProcessing = computed(
    () => fileQueue.value.length > 0 && fileQueue.value.some(f => f.status === 'pending')
  )

  const hasPendingFiles = computed(
    () => fileQueue.value.length > 0
  )

  // Métodos
  const addFile = (file: File): { success: boolean; error?: string } => {
    // Validar
    const validation = validateETLFile(file, options)
    if (!validation.valid) {
      return { success: false, error: validation.error }
    }

    // Verificar duplicados
    if (fileQueue.value.some(f => f.file.name === file.name)) {
      return { success: false, error: `El archivo ${file.name} ya está en la cola` }
    }

    // Agregar
    const id = generateFileId()
    fileQueue.value.push({
      id,
      file,
      status: 'pending',
      progress: 0,
      abortController: new AbortController()
    })

    notifyQueueChange()
    return { success: true }
  }

  const addFiles = (files: File[]) => {
    const results = files.map(f => addFile(f))
    return {
      successful: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length,
      errors: results.filter(r => r.error).map(r => r.error)
    }
  }

  const removeFile = (fileId: string) => {
    const index = fileQueue.value.findIndex(f => f.id === fileId)
    if (index > -1) {
      const file = fileQueue.value[index]
      // Cancelar si está subiendo
      file.abortController?.abort()
      fileQueue.value.splice(index, 1)
      notifyQueueChange()
    }
  }

  const retryFile = (fileId: string) => {
    const file = fileQueue.value.find(f => f.id === fileId)
    if (file) {
      file.status = 'pending'
      file.progress = 0
      file.error = undefined
      file.abortController = new AbortController()
      notifyQueueChange()
    }
  }

  const clearQueue = () => {
    // Cancelar todas las cargas activas
    activeUploads.forEach(controller => controller.abort())
    activeUploads.clear()
    fileQueue.value = []
    notifyQueueChange()
  }

  const updateGlobalProgress = () => {
    const total = fileQueue.value.length
    if (total === 0) {
      globalProgress.value = 0
      return
    }
    const completed = fileQueue.value.reduce((sum, f) => sum + f.progress, 0)
    globalProgress.value = Math.round(completed / total)
  }

  const startProcessing = async () => {
    isProcessing.value = true
    processingComplete.value = false

    try {
      const stats = await uploadFilesParallel(
        fileQueue.value.filter(f => f.status === 'pending').map(f => f.file),
        options,
        (fileIndex, progress) => {
          if (fileQueue.value[fileIndex]) {
            fileQueue.value[fileIndex].progress = progress
            updateGlobalProgress()
            options.onProgress?.(fileIndex, progress)
          }
        },
        (fileIndex, success) => {
          if (fileQueue.value[fileIndex]) {
            fileQueue.value[fileIndex].status = success ? 'completed' : 'error'
            options.onFileComplete?.(fileIndex, success)
          }
        }
      )

      processingComplete.value = true
      notifyQueueChange()
      return stats
    } finally {
      isProcessing.value = false
    }
  }

  const stopProcessing = () => {
    activeUploads.forEach(controller => controller.abort())
    activeUploads.clear()

    fileQueue.value.forEach(f => {
      if (f.status === 'uploading') {
        f.status = 'pending'
        f.progress = 0
      }
    })

    isProcessing.value = false
    notifyQueueChange()
  }

  const reset = () => {
    clearQueue()
    isProcessing.value = false
    processingComplete.value = false
    globalProgress.value = 0
  }

  const notifyQueueChange = () => {
    options.onQueueChange?.(fileQueue.value)
  }

  // Retornar API pública
  return {
    // Estado
    fileQueue,
    isProcessing,
    processingComplete,
    globalProgress,

    // Computed
    completedFilesCount,
    failedFilesCount,
    canStartProcessing,
    hasPendingFiles,

    // Métodos
    addFile,
    addFiles,
    removeFile,
    retryFile,
    clearQueue,
    startProcessing,
    stopProcessing,
    reset,
    updateGlobalProgress
  }
}

/**
 * Ejemplo de uso en componente:
 *
 * <script setup lang="ts">
 * import { useETLUpload } from '@/modules/etl/composables/useETLUpload'
 *
 * const {
 *   fileQueue,
 *   isProcessing,
 *   canStartProcessing,
 *   addFile,
 *   removeFile,
 *   startProcessing
 * } = useETLUpload({
 *   maxFileSize: 50 * 1024 * 1024,
 *   endpoint: '/api/etl/upload',
 *   onProgress: (idx, progress) => console.log(`File ${idx}: ${progress}%`)
 * })
 *
 * const handleFilesSelected = (files: File[]) => {
 *   const result = fileQueue.value.length > 0
 *     ? addFiles(files)
 *     : { successful: 1, failed: 0 }
 *   console.log(`Agregados: ${result.successful}, Fallidos: ${result.failed}`)
 * }
 * </script>
 */

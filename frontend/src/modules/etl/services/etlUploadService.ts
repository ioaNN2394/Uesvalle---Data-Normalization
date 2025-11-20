/**
 * ETL Upload Service
 * Maneja validación, carga y procesamiento de archivos Excel
 */

export interface FileValidationResult {
  valid: boolean
  error?: string
}

export interface UploadProgress {
  fileId: string
  progress: number
  status: 'pending' | 'uploading' | 'completed' | 'error'
}

export interface UploadOptions {
  maxFileSize?: number
  allowedExtensions?: string[]
  allowedMimeTypes?: string[]
  maxParallelUploads?: number
  endpoint?: string
}

// Configuración por defecto
const DEFAULT_OPTIONS: Required<UploadOptions> = {
  maxFileSize: 50 * 1024 * 1024, // 50MB
  allowedExtensions: ['.xlsx', '.xls', '.csv'],
  allowedMimeTypes: [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'application/csv',
    'application/x-csv'
  ],
  maxParallelUploads: 3,
  endpoint: '/api/etl/upload'
}

/**
 * Valida un archivo según las reglas de ETL
 */
export const validateETLFile = (
  file: File,
  options: UploadOptions = {}
): FileValidationResult => {
  const config = { ...DEFAULT_OPTIONS, ...options }

  // Validar extensión
  const fileName = file.name.toLowerCase()
  const hasValidExtension = config.allowedExtensions.some((ext) =>
    fileName.endsWith(ext)
  )

  if (!hasValidExtension) {
    return {
      valid: false,
      error: `Formato no permitido. Solo se aceptan: ${config.allowedExtensions.join(', ')}`
    }
  }

  // Validar MIME type (algunos navegadores reportan tipos variados para .csv)
  if (file.type && !config.allowedMimeTypes.includes(file.type)) {
    return {
      valid: false,
      error: `Tipo de archivo no permitido: ${file.type}`
    }
  }

  // Validar tamaño
  if (file.size > config.maxFileSize) {
    const maxMB = (config.maxFileSize / 1024 / 1024).toFixed(1)
    const fileMB = (file.size / 1024 / 1024).toFixed(2)
    return {
      valid: false,
      error: `Archivo demasiado grande. Máximo: ${maxMB}MB. Tu archivo: ${fileMB}MB`
    }
  }

  return { valid: true }
}

/**
 * Carga un archivo al servidor
 */
export const uploadFile = async (
  file: File,
  options: UploadOptions = {},
  _onProgress?: (progress: number) => void,
  abortSignal?: AbortSignal
): Promise<{ success: boolean; message?: string; data?: any }> => {
  const config = { ...DEFAULT_OPTIONS, ...options }

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(config.endpoint, {
      method: 'POST',
      body: formData,
      signal: abortSignal,
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
        // No establecer Content-Type para que el navegador lo haga automáticamente
      }
    })

    if (!response.ok) {
      throw new Error(
        `Error del servidor: ${response.status} ${response.statusText}`
      )
    }

    const data = await response.json()
    return { success: true, data }
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        return { success: false, message: 'Carga cancelada por el usuario' }
      }
      return { success: false, message: error.message }
    }
    return { success: false, message: 'Error desconocido' }
  }
}

/**
 * Carga múltiples archivos en paralelo (limitando concurrencia)
 */
export const uploadFilesParallel = async (
  files: File[],
  options: UploadOptions = {},
  onFileProgress?: (fileIndex: number, progress: number) => void,
  onFileComplete?: (fileIndex: number, success: boolean) => void,
  abortSignal?: AbortSignal
): Promise<{ completed: number; failed: number; errors: string[] }> => {
  const config = { ...DEFAULT_OPTIONS, ...options }
  const results = { completed: 0, failed: 0, errors: [] as string[] }

  // Procesar en lotes
  for (let i = 0; i < files.length; i += config.maxParallelUploads) {
    const batch = files.slice(i, i + config.maxParallelUploads)

    const promises = batch.map((file, batchIndex) =>
      uploadFile(
        file,
        options,
        (progress) => {
          onFileProgress?.(i + batchIndex, progress)
        },
        abortSignal
      ).then((result) => {
        if (result.success) {
          results.completed++
        } else {
          results.failed++
          if (result.message) {
            results.errors.push(`${file.name}: ${result.message}`)
          }
        }
        onFileComplete?.(i + batchIndex, result.success)
      })
    )

    await Promise.all(promises)
  }

  return results
}

/**
 * Formatea el tamaño de archivo en unidades legibles
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Genera un ID único para archivos
 */
export const generateFileId = (): string => {
  return `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Verifica si el navegador soporta Drag & Drop
 */
export const supportsDragAndDrop = (): boolean => {
  const div = document.createElement('div')
  return (
    ('draggable' in div || ('ondragstart' in div && 'ondrop' in div)) &&
    'FormData' in window &&
    'FileReader' in window
  )
}

/**
 * ETL Upload Module Types
 * Tipos TypeScript para el módulo de carga de ETL
 */

/**
 * Representa un archivo en la cola de carga
 */
export interface QueuedFile {
  /** ID único generado */
  id: string
  /** Objeto File del navegador */
  file: File
  /** Estado actual del archivo */
  status: FileUploadStatus
  /** Progreso de carga 0-100 */
  progress: number
  /** Mensaje de error (si aplica) */
  error?: string
  /** Controlador de cancelación de carga */
  abortController?: AbortController
}

/**
 * Estados posibles de un archivo en carga
 */
export type FileUploadStatus = 'pending' | 'uploading' | 'completed' | 'error'

/**
 * Resultado de validación de archivo
 */
export interface FileValidationResult {
  /** Indica si el archivo es válido */
  valid: boolean
  /** Mensaje de error (si no es válido) */
  error?: string
}

/**
 * Opciones configurables para carga de archivos
 */
export interface UploadOptions {
  /** Tamaño máximo en bytes (default: 50MB) */
  maxFileSize?: number
  /** Extensiones permitidas (default: ['.xlsx', '.xls']) */
  allowedExtensions?: string[]
  /** MIME types permitidos */
  allowedMimeTypes?: string[]
  /** Máximo de cargas paralelas (default: 3) */
  maxParallelUploads?: number
  /** Endpoint del servidor (default: '/api/etl/upload') */
  endpoint?: string
}

/**
 * Respuesta del servidor después de cargar un archivo
 */
export interface UploadResponse {
  /** Indica si la carga fue exitosa */
  success: boolean
  /** Mensaje descriptivo */
  message?: string
  /** Datos adicionales devueltos por el servidor */
  data?: UploadResponseData
}

/**
 * Datos detallados de la respuesta de carga
 */
export interface UploadResponseData {
  /** ID único del archivo en el servidor */
  fileId?: string
  /** Nombre original del archivo */
  fileName?: string
  /** Filas procesadas */
  rowsProcessed?: number
  /** Filas con errores */
  rowsWithErrors?: number
  /** Detalles de errores por fila */
  errors?: RowError[]
}

/**
 * Error en una fila específica del Excel
 */
export interface RowError {
  /** Número de fila */
  row: number
  /** Descripción del error */
  message: string
  /** Columna donde ocurrió el error (opcional) */
  column?: string
}

/**
 * Estadísticas de carga paralela
 */
export interface UploadStats {
  /** Archivos completados exitosamente */
  completed: number
  /** Archivos con error */
  failed: number
  /** Lista de mensajes de error */
  errors: string[]
}

/**
 * Configuración del modal de carga
 */
export interface ETLModalConfig {
  /** Mostrar/ocultar el modal */
  isOpen: boolean
  /** Límite de tamaño de archivo */
  maxFileSize?: number
  /** Extensiones permitidas */
  allowedExtensions?: string[]
  /** Endpoint personalizado */
  endpoint?: string
}

/**
 * Estado global del módulo de carga ETL
 */
export interface ETLUploadState {
  /** Cola de archivos */
  fileQueue: QueuedFile[]
  /** Indica si está en proceso de carga */
  isProcessing: boolean
  /** Indica si el procesamiento se completó */
  processingComplete: boolean
  /** Progreso global 0-100 */
  globalProgress: number
  /** Cantidad de archivos completados */
  completedFilesCount: number
  /** Mostrar diálogo de confirmación */
  showConfirmation: boolean
}

/**
 * Evento de progreso de carga
 */
export interface UploadProgressEvent {
  /** ID del archivo */
  fileId: string
  /** Progreso actual 0-100 */
  progress: number
  /** Estado del archivo */
  status: FileUploadStatus
  /** Error (si aplica) */
  error?: string
}

/**
 * Opciones de confirmación de cancelación
 */
export interface ConfirmationOptions {
  /** Título del diálogo */
  title: string
  /** Mensaje de confirmación */
  message: string
  /** Etiqueta del botón confirmar */
  confirmLabel: string
  /** Etiqueta del botón cancelar */
  cancelLabel: string
  /** Si la acción es destructiva (estilo rojo) */
  isDestructive: boolean
}

/**
 * Configuración de URLs y endpoints del backend
 * Centraliza todas las llamadas API para facilitar cambios
 */

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

export const API_CONFIG = {
  BASE_URL: BACKEND_URL,
  ENDPOINTS: {
    UPLOAD: '/api/etl/upload/',
    JOBS: '/api/etl/jobs/',
    STATUS: '/api/etl/status/',
  }
} as const

/**
 * Construye una URL completa para el backend
 */
export const buildApiUrl = (endpoint: string): string => {
  // En desarrollo, usa rutas relativas (proxy de Vite)
  if (import.meta.env.DEV) {
    return endpoint
  }
  // En producción, usa URL completa
  return `${BACKEND_URL}${endpoint}`
}

/**
 * Configuración para fetch requests
 */
export const API_HEADERS = {
  'Content-Type': 'application/json',
  'X-Requested-With': 'XMLHttpRequest'
} as const
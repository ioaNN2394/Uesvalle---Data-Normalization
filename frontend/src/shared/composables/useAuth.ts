/**
 * Composable para manejar la autenticación de colaboradores
 * Controla el acceso a funciones administrativas (ETL, Notificaciones, Reportes)
 */
import { ref, computed, readonly } from 'vue'
import axios from 'axios'
import { buildApiUrl } from '../config/api.config'

// Estado global de autenticación
const isAuthenticated = ref(false)
const currentUser = ref<{ usuario: string; nombre: string | null } | null>(null)
const authToken = ref<string | null>(null)
const isLoading = ref(false)
const authError = ref<string | null>(null)

// Constantes
const TOKEN_KEY = 'colaborador_token'
const USER_KEY = 'colaborador_user'

/**
 * Inicializar estado desde localStorage
 */
const initAuth = () => {
  const savedToken = localStorage.getItem(TOKEN_KEY)
  const savedUser = localStorage.getItem(USER_KEY)
  
  if (savedToken && savedUser) {
    authToken.value = savedToken
    try {
      currentUser.value = JSON.parse(savedUser)
      isAuthenticated.value = true
      // Verificar que el token siga siendo válido
      verifySession()
    } catch {
      logout()
    }
  }
}

/**
 * Verificar si la sesión actual es válida
 */
const verifySession = async (): Promise<boolean> => {
  if (!authToken.value) return false
  
  try {
    const response = await axios.get(buildApiUrl('/api/core/auth/verify/'), {
      headers: { Authorization: `Bearer ${authToken.value}` }
    })
    
    if (response.data.authenticated) {
      isAuthenticated.value = true
      currentUser.value = {
        usuario: response.data.usuario,
        nombre: response.data.nombre
      }
      return true
    } else {
      logout()
      return false
    }
  } catch {
    logout()
    return false
  }
}

/**
 * Iniciar sesión
 */
const login = async (usuario: string, password: string): Promise<boolean> => {
  isLoading.value = true
  authError.value = null
  
  try {
    const response = await axios.post(buildApiUrl('/api/core/auth/login/'), {
      usuario,
      password
    })
    
    if (response.data.success) {
      authToken.value = response.data.token
      currentUser.value = {
        usuario: response.data.usuario,
        nombre: response.data.nombre
      }
      isAuthenticated.value = true
      
      // Guardar en localStorage
      localStorage.setItem(TOKEN_KEY, response.data.token)
      localStorage.setItem(USER_KEY, JSON.stringify(currentUser.value))
      
      return true
    }
    
    authError.value = response.data.error || 'Error de autenticación'
    return false
  } catch (error: any) {
    authError.value = error.response?.data?.error || 'Error al conectar con el servidor'
    return false
  } finally {
    isLoading.value = false
  }
}

/**
 * Cerrar sesión
 */
const logout = async () => {
  if (authToken.value) {
    try {
      await axios.post(buildApiUrl('/api/core/auth/logout/'), {}, {
        headers: { Authorization: `Bearer ${authToken.value}` }
      })
    } catch {
      // Ignorar errores de logout
    }
  }
  
  // Limpiar estado
  authToken.value = null
  currentUser.value = null
  isAuthenticated.value = false
  authError.value = null
  
  // Limpiar localStorage
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/**
 * Composable de autenticación
 */
export function useAuth() {
  // Inicializar al primer uso
  if (!authToken.value && localStorage.getItem(TOKEN_KEY)) {
    initAuth()
  }
  
  return {
    // Estado (readonly para evitar modificaciones externas)
    isAuthenticated: readonly(isAuthenticated),
    currentUser: readonly(currentUser),
    isLoading: readonly(isLoading),
    authError: readonly(authError),
    
    // Computed
    userName: computed(() => currentUser.value?.nombre || currentUser.value?.usuario || ''),
    
    // Acciones
    login,
    logout,
    verifySession,
    initAuth
  }
}

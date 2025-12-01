<template>
  <Teleport to="body">
    <div v-if="isOpen" class="login-modal-overlay" @click.self="close">
      <div class="login-modal">
        <div class="login-header">
          <div class="login-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
          <h2>Acceso Colaborador</h2>
          <p class="login-subtitle">Inicia sesión para acceder a funciones administrativas</p>
        </div>
        
        <form @submit.prevent="handleLogin" class="login-form">
          <div class="form-group">
            <label for="usuario">Usuario</label>
            <div class="input-wrapper">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <input 
                id="usuario"
                type="text" 
                v-model="usuario" 
                placeholder="Ingresa tu usuario"
                :disabled="isLoading"
                autocomplete="username"
                required
              />
            </div>
          </div>
          
          <div class="form-group">
            <label for="password">Contraseña</label>
            <div class="input-wrapper">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input 
                id="password"
                :type="showPassword ? 'text' : 'password'" 
                v-model="password" 
                placeholder="Ingresa tu contraseña"
                :disabled="isLoading"
                autocomplete="current-password"
                required
              />
              <button 
                type="button" 
                class="toggle-password" 
                @click="showPassword = !showPassword"
                tabindex="-1"
              >
                <svg v-if="showPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div v-if="error" class="error-message">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            {{ error }}
          </div>
          
          <div class="form-actions">
            <button type="button" class="btn-cancel" @click="close" :disabled="isLoading">
              Cancelar
            </button>
            <button type="submit" class="btn-login" :disabled="isLoading || !usuario || !password">
              <span v-if="isLoading" class="loading-spinner"></span>
              <span v-else>Iniciar Sesión</span>
            </button>
          </div>
        </form>
        
        <button class="close-btn" @click="close" aria-label="Cerrar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAuth } from '@/shared/composables/useAuth'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'login-success'): void
}>()

const { login, authError } = useAuth()

const usuario = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const isLoading = ref(false)

// Limpiar formulario al abrir
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    usuario.value = ''
    password.value = ''
    error.value = ''
    showPassword.value = false
  }
})

const close = () => {
  emit('close')
}

const handleLogin = async () => {
  if (!usuario.value || !password.value) return
  
  isLoading.value = true
  error.value = ''
  
  const success = await login(usuario.value, password.value)
  
  isLoading.value = false
  
  if (success) {
    emit('login-success')
    close()
  } else {
    error.value = authError.value || 'Error al iniciar sesión'
  }
}
</script>

<style scoped>
.login-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 20px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.login-modal {
  background: linear-gradient(145deg, #1e293b, #0f172a);
  border-radius: 16px;
  width: 100%;
  max-width: 400px;
  padding: 32px;
  position: relative;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { 
    opacity: 0;
    transform: translateY(20px) scale(0.98);
  }
  to { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.login-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #0ea5a4, #0d9488);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  color: white;
}

.login-header h2 {
  margin: 0 0 8px 0;
  font-size: 22px;
  font-weight: 600;
  color: #f1f5f9;
}

.login-subtitle {
  margin: 0;
  font-size: 14px;
  color: #94a3b8;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: #cbd5e1;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper svg {
  position: absolute;
  left: 14px;
  color: #64748b;
  pointer-events: none;
}

.input-wrapper input {
  width: 100%;
  padding: 14px 14px 14px 44px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #f1f5f9;
  font-size: 14px;
  transition: all 0.2s ease;
}

.input-wrapper input::placeholder {
  color: #64748b;
}

.input-wrapper input:focus {
  outline: none;
  border-color: #0ea5a4;
  background: rgba(14, 165, 164, 0.05);
  box-shadow: 0 0 0 3px rgba(14, 165, 164, 0.1);
}

.input-wrapper input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-password {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s ease;
}

.toggle-password:hover {
  color: #94a3b8;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #ef4444;
  font-size: 13px;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.btn-cancel,
.btn-login {
  flex: 1;
  padding: 14px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
}

.btn-cancel:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: #f1f5f9;
}

.btn-login {
  background: linear-gradient(135deg, #0ea5a4, #0d9488);
  border: none;
  color: white;
}

.btn-login:hover:not(:disabled) {
  background: linear-gradient(135deg, #14b8a6, #0ea5a4);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(14, 165, 164, 0.3);
}

.btn-login:disabled,
.btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.05);
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

@media (max-width: 480px) {
  .login-modal {
    padding: 24px;
    max-width: 100%;
  }
  
  .form-actions {
    flex-direction: column-reverse;
  }
}
</style>

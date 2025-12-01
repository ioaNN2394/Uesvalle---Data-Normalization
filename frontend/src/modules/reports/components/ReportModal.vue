// src/modules/reports/components/ReportModal.vue
<template>
  <div class="modal-overlay" @click.self="close">
    <div class="report-modal">
      <h2 class="modal-title">Generación de Reporte</h2>
      <form class="modal-form" @submit.prevent>
        <div class="fields-grid">
          <div v-for="field in fields" :key="field.key" class="modal-field">
            <label class="modal-label">{{ field.label }}</label>
            
            <!-- Selector para Año y Calendario -->
            <div v-if="field.type === 'select'" class="modal-input-group">
              <select class="modal-select" v-model="form[field.key]">
                <option value="" selected>Dejar en blanco o seleccionar</option>
                <option v-for="option in field.options" :key="option" :value="option">
                  {{ option }}
                </option>
              </select>
            </div>

            <!-- Input de texto para los demás campos -->
            <div v-else class="modal-input-group">
              <input
                class="modal-input"
                :placeholder="'Dejar en blanco generara un reporte general'"
                v-model="form[field.key]"
                type="text"
              />
              <button type="button" class="modal-search-btn">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-icon" @click="generateReport('excel')" :disabled="isGenerating" title="Exportar a Excel">
            <img :src="xlsIcon" alt="Exportar a XLS" class="action-icon" />
          </button>
          <button type="button" class="btn-icon" @click="generateReport('pdf')" :disabled="isGenerating" title="Exportar a PDF">
            <img :src="pdfIcon" alt="Exportar a PDF" class="action-icon" />
          </button>
        </div>
      </form>

      <!-- Status Overlay -->
      <div v-if="isGenerating || reportStatus" class="status-overlay-inner">
        <div class="status-content">
          <h3 v-if="isGenerating">Generando Reporte...</h3>
          <div v-if="isGenerating" class="progress-bar">
            <div class="progress-fill" :style="{ width: generationProgress + '%' }"></div>
          </div>
          <p v-if="reportStatus === 'success'" class="success-text">
            ✅ ¡Reporte listo! Descargando...
          </p>
          <p v-if="reportStatus === 'error'" class="error-text">
            ❌ Error: {{ errorMessage }}
          </p>
          <button v-if="!isGenerating" @click="closeStatus" class="btn-close-status">Cerrar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineEmits, reactive, ref } from 'vue'
import axios from 'axios'
import { buildApiUrl } from '@/shared/config/api.config'
import xlsIcon from '@/assets/icons/xls.png'
import pdfIcon from '@/assets/icons/pdf.png'

const emit = defineEmits(['close'])
const close = () => emit('close')

// Estado de generación
const isGenerating = ref(false)
const generationProgress = ref(0)
const reportStatus = ref<'success' | 'error' | null>(null)
const errorMessage = ref('')
const currentTaskId = ref('')

type FieldKey =
  | 'anio'
  | 'institucion'
  | 'pae'
  | 'municipio'
  | 'estado'
  | 'calendario'
  | 'nivel'
  | 'concepto'

interface Field {
  key: FieldKey
  label: string
  type?: 'text' | 'select'
  options?: (string | number)[]
}

// --- Opciones para los selectores ---
const currentYear = new Date().getFullYear();
const years = Array.from({ length: 20 }, (_, i) => currentYear - i);
const calendarOptions = ['A', 'B'];

const fields: Field[] = [
  { key: 'anio', label: 'Año', type: 'select', options: years },
  { key: 'institucion', label: 'Institución', type: 'text' },
  { key: 'pae', label: 'PAE', type: 'text' },
  { key: 'municipio', label: 'Municipio', type: 'text' },
  { key: 'estado', label: 'Estado', type: 'text' },
  { key: 'calendario', label: 'Calendario', type: 'select', options: calendarOptions },
  { key: 'nivel', label: 'Nivel', type: 'text' },
  { key: 'concepto', label: 'Concepto Sanitario', type: 'text' }
]

const form = reactive<Record<FieldKey, string>>({
  anio: '',
  institucion: '',
  pae: '',
  municipio: '',
  estado: '',
  calendario: '',
  nivel: '',
  concepto: ''
})

// Función principal de generación de reporte
const generateReport = async (format: 'excel' | 'pdf') => {
  isGenerating.value = true
  generationProgress.value = 0
  reportStatus.value = null
  errorMessage.value = ''

  // Preparar filtros para el backend
  const filters = {
    anios: form.anio ? [parseInt(form.anio)] : [],
    municipios: form.municipio ? [form.municipio] : [],
    estados: form.estado ? [form.estado] : [],
    conceptos_visita: form.concepto ? [form.concepto] : [],
    calendario: form.calendario || null,
    nivel: form.nivel || null,
    tiene_pae: form.pae ? (form.pae.toLowerCase() === 'si' || form.pae.toLowerCase() === 'sí' ? true : form.pae.toLowerCase() === 'no' ? false : null) : null,
    instituciones: []
  }

  try {
    const response = await axios.post(buildApiUrl('/api/reports/generate/'), {
      format: format,
      filters: filters
    })

    if (response.data.task_id) {
      currentTaskId.value = response.data.task_id
      checkReportStatus(response.data.task_id)
    } else if (response.data.warning) {
      // Si hay advertencia de muchos registros, proceder de todos modos
      const confirmResponse = await axios.post(buildApiUrl('/api/reports/generate/'), {
        format: format,
        filters: filters,
        confirm: true
      })
      if (confirmResponse.data.task_id) {
        currentTaskId.value = confirmResponse.data.task_id
        checkReportStatus(confirmResponse.data.task_id)
      }
    }
  } catch (error: any) {
    console.error('Error generando reporte:', error)
    isGenerating.value = false
    reportStatus.value = 'error'
    
    // Manejo de errores específicos
    if (error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED') {
      errorMessage.value = 'No se puede conectar al servidor. Asegúrate de que el backend está corriendo en http://localhost:8000'
    } else if (error.response?.status === 404) {
      errorMessage.value = 'Endpoint no encontrado. Verifica la configuración del backend'
    } else if (error.response?.status === 500) {
      errorMessage.value = `Error en el servidor: ${error.response.data?.detail || error.response.data?.error || 'Error desconocido'}`
    } else if (error.message?.includes('Connection refused')) {
      errorMessage.value = 'La conexión fue rechazada. ¿El backend está corriendo?'
    } else {
      errorMessage.value = error.response?.data?.error || error.message || 'Error al iniciar la generación del reporte'
    }
  }
}

// Verificar estado del reporte (polling)
const checkReportStatus = async (taskId: string, attempt = 0) => {
  if (attempt > 300) {
    reportStatus.value = 'error'
    errorMessage.value = 'Tiempo de espera agotado'
    isGenerating.value = false
    return
  }

  try {
    const response = await axios.get(buildApiUrl(`/api/reports/status/${taskId}/`))
    const data = response.data

    if (data.status === 'processing' || data.status === 'pending') {
      generationProgress.value = data.progress || Math.min(attempt * 2, 90)
      setTimeout(() => checkReportStatus(taskId, attempt + 1), 1000)
    } else if (data.status === 'success') {
      isGenerating.value = false
      generationProgress.value = 100
      reportStatus.value = 'success'
      
      // Descargar automáticamente
      if (data.download_url) {
        setTimeout(() => {
          window.location.href = data.download_url
        }, 500)
      }
    } else if (data.status === 'failed' || data.status === 'error') {
      isGenerating.value = false
      reportStatus.value = 'error'
      errorMessage.value = data.error || 'Error desconocido'
    }
  } catch (error) {
    // Reintentar en caso de error de red
    setTimeout(() => checkReportStatus(taskId, attempt + 1), 2000)
  }
}

const closeStatus = () => {
  reportStatus.value = null
  isGenerating.value = false
  errorMessage.value = ''
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.2);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.report-modal {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1);
  padding: 24px 32px;
  width: 100%;
  max-width: 720px;
  display: flex;
  flex-direction: column;
}

.modal-title {
  font-size: 24px;
  font-weight: 700;
  text-align: center;
  margin: 0 0 24px 0;
  color: #111827;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
  align-items: flex-start;
  width: 100%;
}

.fields-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px 20px;
  width: 100%;
}

.modal-field {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.modal-label {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
  color: #374151;
  text-align: left;
}

.modal-input-group {
  display: flex;
  align-items: center;
  width: 100%;
  background-color: #f3f4f6;
  border-radius: 8px;
  border: 1px solid transparent;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.modal-input-group:focus-within {
  border-color: #a5b4fc;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.modal-input {
  flex: 1;
  padding: 10px 12px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #111827;
  outline: none;
}

.modal-input::placeholder {
  color: #9ca3af;
  font-size: 13px;
}

/* --- Estilos para el SELECT --- */
.modal-select {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  
  width: 100%;
  padding: 10px 32px 10px 12px; /* Espacio para la flecha */
  border: none;
  background-color: transparent;
  font-size: 14px;
  color: #111827;
  outline: none;
  cursor: pointer;

  background-image: url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%236b7280%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E');
  background-repeat: no-repeat;
  background-position: right 12px top 50%;
  background-size: .65em auto;
}

/* Color del texto cuando no hay nada seleccionado */
.modal-select:invalid,
.modal-select option[value=""] {
  color: #9ca3af;
}

.modal-search-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-start;
}

.btn-icon {
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  transition: opacity 0.2s;
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon:hover:not(:disabled) {
  opacity: 0.8;
}

/* Status Overlay */
.status-overlay-inner {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.status-content {
  text-align: center;
  padding: 32px;
}

.status-content h3 {
  font-size: 18px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 16px;
}

.progress-bar {
  width: 200px;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin: 0 auto 16px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.success-text {
  color: #059669;
  font-weight: 600;
  font-size: 16px;
}

.error-text {
  color: #dc2626;
  font-weight: 500;
  font-size: 14px;
  max-width: 300px;
}

.btn-close-status {
  margin-top: 16px;
  padding: 8px 24px;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-close-status:hover {
  background: #4f46e5;
}

/* Make modal position relative for overlay */
.report-modal {
  position: relative;
}

</style>
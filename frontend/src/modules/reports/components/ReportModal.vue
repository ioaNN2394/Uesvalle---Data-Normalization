// src/modules/reports/components/ReportModal.vue
<template>
  <div class="modal-overlay" @click.self="close">
    <div class="report-modal">
      <h2 class="modal-title">Generación de Reporte</h2>
      <form class="modal-form" @submit.prevent>
        <div class="fields-grid">
          <!-- Municipio con búsqueda dinámica -->
          <div class="modal-field">
            <label class="modal-label">Municipio</label>
            <div class="modal-input-group">
              <input
                class="modal-input"
                placeholder="Dejar en blanco o buscar"
                v-model="form.municipio"
                @input="handleMunicipioSearch"
                @focus="showMunicipioDropdown = true"
                @blur="handleMunicipioBlur"
                type="text"
              />
              <div v-if="showMunicipioDropdown && municipioOptions.length > 0" class="search-dropdown">
                <div
                  v-for="option in municipioOptions"
                  :key="option.codigo"
                  class="dropdown-item"
                  @click="selectMunicipio(option)"
                >
                  {{ option.nombre }}
                </div>
              </div>
              <button type="button" class="modal-search-btn" @click="showMunicipioDropdown = !showMunicipioDropdown">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Concepto Visita como Combobox -->
          <div class="modal-field">
            <label class="modal-label">Concepto Visita</label>
            <div class="modal-input-group">
              <select class="modal-select" v-model="form.conceptoVisita">
                <option value="">Dejar en blanco o seleccionar</option>
                <option value="F">Favorable</option>
                <option value="D">Desfavorable</option>
                <option value="FCR">Favorable con Requerimientos</option>
              </select>
            </div>
          </div>

          <!-- Rango de Fechas -->
          <div class="modal-field">
            <label class="modal-label">Fecha Inicio</label>
            <div class="modal-input-group">
              <input
                class="modal-input"
                placeholder="YYYY-MM-DD o dejar en blanco"
                v-model="form.fechaInicio"
                type="date"
                :max="today"
              />
            </div>
          </div>

          <div class="modal-field">
            <label class="modal-label">Fecha Fin</label>
            <div class="modal-input-group">
              <input
                class="modal-input"
                placeholder="YYYY-MM-DD o dejar en blanco"
                v-model="form.fechaFin"
                type="date"
                :max="today"
              />
            </div>
          </div>

          <!-- Institución con búsqueda dinámica -->
          <div class="modal-field">
            <label class="modal-label">Institución</label>
            <div class="modal-input-group">
              <input
                class="modal-input"
                placeholder="Buscar por DANE, ID o nombre"
                v-model="form.institucion"
                @input="handleInstitucionSearch"
                @focus="showInstitucionDropdown = true"
                @blur="handleInstitucionBlur"
                type="text"
              />
              <div v-if="showInstitucionDropdown && institucionOptions.length > 0" class="search-dropdown">
                <div
                  v-for="option in institucionOptions"
                  :key="option.id"
                  class="dropdown-item"
                  @click="selectInstitucion(option)"
                >
                  <div class="dropdown-item-title">{{ option.nombre }}</div>
                  <div class="dropdown-item-subtitle">DANE: {{ option.dane }} | ID: {{ option.id }}</div>
                </div>
              </div>
              <button type="button" class="modal-search-btn" @click="showInstitucionDropdown = !showInstitucionDropdown">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Estado como Combobox -->
          <div class="modal-field">
            <label class="modal-label">Estado</label>
            <div class="modal-input-group">
              <select class="modal-select" v-model="form.estado">
                <option value="">Dejar en blanco o seleccionar</option>
                <option value="ACTIVA">Activa</option>
                <option value="CIERRE TEMPORAL">Cierre Temporal</option>
                <option value="CIERRE DEFINITIVO">Cierre Definitivo</option>
                <option value="NO DEFINIDO">No Definido</option>
                <option value="DUPLICADO">Duplicado</option>
              </select>
            </div>
          </div>

          <!-- Tiene PAE como Combobox -->
          <div class="modal-field">
            <label class="modal-label">Tiene PAE</label>
            <div class="modal-input-group">
              <select class="modal-select" v-model="form.tienePae">
                <option value="">Dejar en blanco o seleccionar</option>
                <option value="SI">Sí</option>
                <option value="NO">No</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Mensaje de advertencia si no hay datos -->
        <div v-if="validationWarning" class="warning-message">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3.05h16.94a2 2 0 0 0 1.71-3.05L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ validationWarning }}
        </div>

        <div class="modal-actions">
          <button 
            type="button" 
            class="btn-icon" 
            @click="generateReport('excel')" 
            :disabled="isGenerating || !!validationWarning" 
            title="Exportar a Excel"
          >
            <img :src="xlsIcon" alt="Exportar a XLS" class="action-icon" />
          </button>
          <button 
            type="button" 
            class="btn-icon" 
            @click="generateReport('pdf')" 
            :disabled="isGenerating || !!validationWarning" 
            title="Exportar a PDF"
          >
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

      <!-- Modal de Confirmación -->
      <div v-if="showConfirmModal" class="confirmation-overlay">
        <div class="confirmation-modal">
          <h3 class="confirmation-title">Confirmar Generación de Reporte</h3>
          <p class="confirmation-message">{{ confirmationMessage }}</p>
          <div class="confirmation-actions">
            <button @click="cancelGeneration" class="btn-cancel">No, cancelar</button>
            <button @click="confirmGeneration" class="btn-confirm">Sí, generar reporte</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineEmits, reactive, ref, computed } from 'vue'
import axios from 'axios'
import { buildApiUrl } from '@/shared/config/api.config'
import xlsIcon from '@/assets/icons/xls.png'
import pdfIcon from '@/assets/icons/pdf.png'

const emit = defineEmits(['close'])
const close = () => emit('close')

// Calcular fecha de hoy para limitar el máximo de las fechas
const today = computed(() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
})

// Estado de generación
const isGenerating = ref(false)
const generationProgress = ref(0)
const reportStatus = ref<'success' | 'error' | null>(null)
const errorMessage = ref('')
const currentTaskId = ref('')
const validationWarning = ref('')
const showConfirmModal = ref(false)
const pendingFormat = ref<'excel' | 'pdf' | null>(null)
const pendingFilters = ref<any>(null)
const confirmationMessage = ref('')

// Dropdowns
const showMunicipioDropdown = ref(false)
const showInstitucionDropdown = ref(false)

// Opciones de búsqueda
const municipioOptions = ref<Array<{ codigo: string; nombre: string }>>([])
const institucionOptions = ref<Array<{ id: string; nombre: string; dane: string }>>([])

// Formulario
const form = reactive({
  municipio: '',
  conceptoVisita: '',
  fechaInicio: '',
  fechaFin: '',
  institucion: '',
  estado: '',
  tienePae: ''
})

// Función para cargar opciones de municipios
const loadMunicipios = async () => {
  try {
    const response = await axios.get(buildApiUrl('/api/reports/generate/'))
    if (response.data.filter_options?.municipios) {
      municipioOptions.value = response.data.filter_options.municipios
    }
  } catch (error) {
    console.error('Error cargando municipios:', error)
  }
}

// Función para cargar opciones de instituciones
const loadInstituciones = async () => {
  try {
    const response = await axios.get(buildApiUrl('/api/reports/instituciones/'))
    if (Array.isArray(response.data.results)) {
      institucionOptions.value = response.data.results.map((inst: any) => ({
        id: inst.id,
        nombre: inst.nombre,
        dane: inst.dane || ''
      }))
    }
  } catch (error) {
    console.error('Error cargando instituciones:', error)
  }
}

// Manejar búsqueda de municipio
const handleMunicipioSearch = (event: Event) => {
  const input = (event.target as HTMLInputElement).value.toLowerCase()
  
  if (!input) {
    loadMunicipios()
    return
  }

  municipioOptions.value = municipioOptions.value.filter(m =>
    m.nombre.toLowerCase().includes(input) ||
    m.codigo.toLowerCase().includes(input)
  )
}

// Manejar búsqueda de institución
const handleInstitucionSearch = (event: Event) => {
  const input = (event.target as HTMLInputElement).value.toLowerCase()
  
  if (!input) {
    loadInstituciones()
    return
  }

  institucionOptions.value = institucionOptions.value.filter(inst =>
    inst.nombre.toLowerCase().includes(input) ||
    inst.dane.toLowerCase().includes(input) ||
    inst.id.toLowerCase().includes(input)
  )
}

// Seleccionar municipio
const selectMunicipio = (option: { codigo: string; nombre: string }) => {
  form.municipio = option.nombre
  showMunicipioDropdown.value = false
  validateFilters()
}

// Seleccionar institución
const selectInstitucion = (option: { id: string; nombre: string; dane: string }) => {
  form.institucion = option.nombre
  showInstitucionDropdown.value = false
  validateFilters()
}

// Manejar blur del municipio con delay
const handleMunicipioBlur = () => {
  window.setTimeout(() => {
    showMunicipioDropdown.value = false
  }, 200)
}

// Manejar blur de la institución con delay
const handleInstitucionBlur = () => {
  window.setTimeout(() => {
    showInstitucionDropdown.value = false
  }, 200)
}

// Validar que los filtros no retornan datos vacíos
const validateFilters = async () => {
  // Si no hay filtros, no validar
  if (!form.municipio && !form.conceptoVisita && !form.fecha && 
      !form.institucion && !form.estado && !form.tienePae) {
    validationWarning.value = ''
    return
  }

  // Por ahora, mostrar advertencia si se usan filtros que pueden no devolver resultados
  // En una versión más avanzada, hacer una consulta previa al backend
  validationWarning.value = ''
}

// Función principal de generación de reporte
const generateReport = async (format: 'excel' | 'pdf') => {
  // Preparar filtros para el backend
  const filters: any = {
    municipios: form.municipio ? [form.municipio] : [],
    conceptos_visita: form.conceptoVisita ? [form.conceptoVisita] : [],
    fecha_inicio: form.fechaInicio ? form.fechaInicio : null,
    fecha_fin: form.fechaFin ? form.fechaFin : null,
    instituciones: form.institucion ? [form.institucion] : [],
    estados: form.estado ? [form.estado] : [],
    tiene_pae: form.tienePae === 'SI' ? true : form.tienePae === 'NO' ? false : null
  }

  // Si no hay filtros y no hay confirmación previa, mostrar modal de confirmación
  if (!form.municipio && !form.conceptoVisita && !form.fechaInicio && !form.fechaFin && 
      !form.institucion && !form.estado && !form.tienePae) {
    // Hacer una consulta previa para obtener el count
    try {
      const response = await axios.post(buildApiUrl('/api/reports/generate/'), {
        format: format,
        filters: filters,
        dry_run: true
      })

      if (response.data.action_required) {
        showConfirmModal.value = true
        confirmationMessage.value = response.data.warning || `No has seleccionado ningún filtro. Se generará un reporte de las ${response.data.total_count || 'muchas'} instituciones. ¿Deseas continuar?`
        pendingFormat.value = format
        pendingFilters.value = filters
        return
      }
    } catch (error) {
      console.error('Error verificando filtros:', error)
    }
  }

  isGenerating.value = true
  generationProgress.value = 0
  reportStatus.value = null
  errorMessage.value = ''

  try {
    const response = await axios.post(buildApiUrl('/api/reports/generate/'), {
      format: format,
      filters: filters
    })

    if (response.data.task_id) {
      currentTaskId.value = response.data.task_id
      checkReportStatus(response.data.task_id)
    }
  } catch (error: any) {
    console.error('Error generando reporte:', error)
    isGenerating.value = false
    reportStatus.value = 'error'
    
    // Manejo de errores específicos
    if (error.response?.data?.error?.includes('no data') || error.response?.status === 400) {
      errorMessage.value = 'No se encontraron datos que coincidan con los filtros seleccionados. Por favor, verifica tus filtros.'
    } else if (error.code === 'ERR_NETWORK') {
      errorMessage.value = 'No se puede conectar al servidor'
    } else if (error.response?.status === 500) {
      errorMessage.value = `Error en el servidor: ${error.response.data?.detail || 'Error desconocido'}`
    } else {
      errorMessage.value = error.response?.data?.error || 'Error al iniciar la generación del reporte'
    }
  }
}

// Confirmar generación después de modal
const confirmGeneration = async () => {
  if (!pendingFormat.value || !pendingFilters.value) {
    return
  }

  showConfirmModal.value = false
  isGenerating.value = true
  generationProgress.value = 0
  reportStatus.value = null
  errorMessage.value = ''

  try {
    const response = await axios.post(buildApiUrl('/api/reports/generate/'), {
      format: pendingFormat.value,
      filters: pendingFilters.value,
      confirm: true
    })

    if (response.data.task_id) {
      currentTaskId.value = response.data.task_id
      checkReportStatus(response.data.task_id)
    } else {
      reportStatus.value = 'error'
      errorMessage.value = 'No se recibió un ID de tarea del servidor'
      isGenerating.value = false
    }
  } catch (error: any) {
    console.error('Error generando reporte:', error)
    isGenerating.value = false
    reportStatus.value = 'error'
    
    if (error.response?.data?.error?.includes('no data') || error.response?.status === 400) {
      errorMessage.value = 'No se encontraron datos que coincidan con los filtros seleccionados. Por favor, verifica tus filtros.'
    } else if (error.code === 'ERR_NETWORK') {
      errorMessage.value = 'No se puede conectar al servidor'
    } else if (error.response?.status === 500) {
      errorMessage.value = `Error en el servidor: ${error.response.data?.detail || 'Error desconocido'}`
    } else {
      errorMessage.value = error.response?.data?.error || 'Error al iniciar la generación del reporte'
    }
  } finally {
    pendingFormat.value = null
    pendingFilters.value = null
  }
}

// Cancelar confirmación
const cancelGeneration = () => {
  showConfirmModal.value = false
  pendingFormat.value = null
  pendingFilters.value = null
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

    console.log('Report status response:', data)

    if (data.status === 'processing' || data.status === 'pending') {
      generationProgress.value = data.progress || Math.min(attempt * 2, 90)
      window.setTimeout(() => checkReportStatus(taskId, attempt + 1), 1000)
    } else if (data.status === 'success') {
      isGenerating.value = false
      generationProgress.value = 100
      reportStatus.value = 'success'
      
      // Descargar automáticamente
      if (data.download_url) {
        window.setTimeout(() => {
          window.location.href = data.download_url
        }, 500)
      }
    } else if (data.status === 'failed' || data.status === 'error') {
      isGenerating.value = false
      reportStatus.value = 'error'
      errorMessage.value = data.error || 'Error desconocido'
    } else {
      // Status desconocido, reintentar
      window.setTimeout(() => checkReportStatus(taskId, attempt + 1), 1000)
    }
  } catch (error: any) {
    console.error('Error checking report status:', error)
    // Reintentar en caso de error de red
    if (attempt < 300) {
      window.setTimeout(() => checkReportStatus(taskId, attempt + 1), 2000)
    } else {
      isGenerating.value = false
      reportStatus.value = 'error'
      errorMessage.value = 'Error al verificar el estado del reporte'
    }
  }
}

const closeStatus = () => {
  reportStatus.value = null
  isGenerating.value = false
  errorMessage.value = ''
}

// Cargar datos iniciales
loadMunicipios()
loadInstituciones()
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
  position: relative;
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
  position: relative;
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
  position: relative;
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

/* Estilos para el SELECT */
.modal-select {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  
  width: 100%;
  padding: 10px 32px 10px 12px;
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

.modal-select:invalid,
.modal-select option[value=""] {
  color: #9ca3af;
}

/* Dropdown de búsqueda */
.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e5e7eb;
  border-top: none;
  border-radius: 0 0 8px 8px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 10;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.dropdown-item {
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.2s;
  border-bottom: 1px solid #f3f4f6;
  color: #111827;
}

.dropdown-item:hover {
  background-color: #f0f1f3;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item-title {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
}

.dropdown-item-subtitle {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
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
  flex-shrink: 0;
}

.modal-search-btn:hover {
  color: #374151;
}

/* Advertencia */
.warning-message {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  color: #92400e;
  font-size: 14px;
  font-weight: 500;
  width: 100%;
}

.warning-message svg {
  flex-shrink: 0;
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

.action-icon {
  width: 48px;
  height: 48px;
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

/* Confirmation Modal */
.confirmation-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.confirmation-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px rgba(0, 0, 0, 0.2);
  padding: 32px;
  max-width: 500px;
  width: 90%;
  text-align: center;
}

.confirmation-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 16px 0;
}

.confirmation-message {
  font-size: 16px;
  color: #374151;
  line-height: 1.5;
  margin: 0 0 24px 0;
}

.confirmation-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.btn-cancel {
  padding: 10px 24px;
  background: #e5e7eb;
  color: #374151;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  font-size: 14px;
  transition: background 0.2s;
}

.btn-cancel:hover {
  background: #d1d5db;
}

.btn-confirm {
  padding: 10px 24px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  font-size: 14px;
  transition: background 0.2s;
}

.btn-confirm:hover {
  background: #059669;
}
</style>
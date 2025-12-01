<template>
  <div class="report-modal">
    <h2 class="modal-title">Generación de Reporte</h2>
    <form class="modal-form" @submit.prevent>
      <div class="fields-grid">
        
        <!-- Año -->
        <div class="modal-field">
          <label class="modal-label">Año</label>
          <div class="modal-input-group">
            <select v-model="selectedFilters.anio" class="modal-select">
              <option value="">Dejar en blanco o seleccionar</option>
              <option v-for="year in yearsRange" :key="year" :value="year">{{ year }}</option>
            </select>
          </div>
        </div>

        <!-- Institución -->
        <div class="modal-field">
          <label class="modal-label">Institución</label>
          <div class="modal-input-group">
            <input 
              v-model="institutionSearch" 
              class="modal-input" 
              placeholder="Dejar en blanco generara un reporte general" 
              type="text"
              @input="onInstitutionInput"
            >
            <button type="button" class="modal-search-btn" @click="searchInstitutions">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
            </button>
          </div>
          <!-- Dropdown de resultados de búsqueda -->
          <div v-if="foundInstitutions.length > 0" class="search-results">
            <div 
              v-for="inst in foundInstitutions" 
              :key="inst.id" 
              class="search-item"
              @click="selectInstitution(inst)"
            >
              {{ inst.nombre }}
            </div>
          </div>
        </div>

        <!-- PAE -->
        <div class="modal-field">
          <label class="modal-label">PAE</label>
          <div class="modal-input-group">
            <input 
              v-model="paeDisplay" 
              class="modal-input" 
              placeholder="Dejar en blanco generara un reporte general" 
              type="text"
              readonly
              @click="togglePaeOptions"
            >
            <button type="button" class="modal-search-btn" @click="togglePaeOptions">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
            </button>
          </div>
          <div v-if="showPaeOptions" class="search-results">
            <div class="search-item" @click="selectPae(true)">Con PAE</div>
            <div class="search-item" @click="selectPae(false)">Sin PAE</div>
            <div class="search-item" @click="selectPae(null)">Todos</div>
          </div>
        </div>

        <!-- Municipio -->
        <div class="modal-field">
          <label class="modal-label">Municipio</label>
          <div class="modal-input-group">
            <input 
              v-model="municipioSearch" 
              class="modal-input" 
              placeholder="Dejar en blanco generara un reporte general" 
              type="text"
              @input="filterMunicipios"
              @focus="showMunicipioOptions = true"
            >
            <button type="button" class="modal-search-btn" @click="showMunicipioOptions = !showMunicipioOptions">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
            </button>
          </div>
          <div v-if="showMunicipioOptions && filteredMunicipios.length > 0" class="search-results">
            <div 
              v-for="mun in filteredMunicipios" 
              :key="mun.codigo" 
              class="search-item"
              @click="selectMunicipio(mun)"
            >
              {{ mun.nombre }}
            </div>
          </div>
        </div>

        <!-- Estado -->
        <div class="modal-field">
          <label class="modal-label">Estado</label>
          <div class="modal-input-group">
            <input 
              v-model="estadoSearch" 
              class="modal-input" 
              placeholder="Dejar en blanco generara un reporte general" 
              type="text"
              @input="filterEstados"
              @focus="showEstadoOptions = true"
            >
            <button type="button" class="modal-search-btn" @click="showEstadoOptions = !showEstadoOptions">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
            </button>
          </div>
          <div v-if="showEstadoOptions && filteredEstados.length > 0" class="search-results">
            <div 
              v-for="est in filteredEstados" 
              :key="est" 
              class="search-item"
              @click="selectEstado(est)"
            >
              {{ est }}
            </div>
          </div>
        </div>

        <!-- Calendario -->
        <div class="modal-field">
          <label class="modal-label">Calendario</label>
          <div class="modal-input-group">
            <select v-model="selectedFilters.calendario" class="modal-select">
              <option value="">Dejar en blanco o seleccionar</option>
              <option value="A">A</option>
              <option value="B">B</option>
            </select>
          </div>
        </div>

        <!-- Nivel -->
        <div class="modal-field">
          <label class="modal-label">Nivel</label>
          <div class="modal-input-group">
            <input 
              v-model="selectedFilters.nivel" 
              class="modal-input" 
              placeholder="Dejar en blanco generara un reporte general" 
              type="text"
            >
            <button type="button" class="modal-search-btn">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
            </button>
          </div>
        </div>

        <!-- Concepto Sanitario -->
        <div class="modal-field">
          <label class="modal-label">Concepto Sanitario</label>
          <div class="modal-input-group">
            <input 
              v-model="conceptoSearch" 
              class="modal-input" 
              placeholder="Dejar en blanco generara un reporte general" 
              type="text"
              @input="filterConceptos"
              @focus="showConceptoOptions = true"
            >
            <button type="button" class="modal-search-btn" @click="showConceptoOptions = !showConceptoOptions">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
            </button>
          </div>
          <div v-if="showConceptoOptions && filteredConceptos.length > 0" class="search-results">
            <div 
              v-for="con in filteredConceptos" 
              :key="con.value" 
              class="search-item"
              @click="selectConcepto(con)"
            >
              {{ con.label }}
            </div>
          </div>
        </div>

      </div>

      <div class="modal-actions">
        <button type="button" class="btn-icon" @click="generateReport('excel')" :disabled="isGenerating">
          <img src="/xls.png" alt="Exportar a XLS" class="action-icon">
        </button>
        <button type="button" class="btn-icon" @click="generateReport('pdf')" :disabled="isGenerating">
          <img src="/pdf.png" alt="Exportar a PDF" class="action-icon">
        </button>
      </div>
    </form>

    <!-- Estado de generación (Overlay o sección inferior) -->
    <div v-if="isGenerating || reportTask" class="status-overlay">
      <div class="status-content">
        <h3>Generando Reporte...</h3>
        <div v-if="isGenerating" class="progress-bar">
          <div class="progress-fill" :style="{ width: generationProgress + '%' }"></div>
        </div>
        <p v-if="reportTask && reportTask.status === 'success'">
           ¡Reporte listo! Descargando...
        </p>
        <p v-if="reportTask && (reportTask.status === 'error' || reportTask.status === 'failed')" class="error-text">
           Error: {{ reportTask.error }}
        </p>
        <button v-if="!isGenerating" @click="closeStatus" class="btn-close-status">Cerrar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import axios from 'axios'

// Estado
const filterOptions = reactive({
  municipios: [],
  conceptos_visita: [],
  anios: [],
  estados: [],
  tiene_pae: []
})

const selectedFilters = reactive({
  anio: '',
  instituciones: [], // IDs
  municipios: [], // Códigos
  estados: [],
  tiene_pae: null,
  calendario: '',
  nivel: '',
  conceptos_visita: []
})

// UI State
const institutionSearch = ref('')
const foundInstitutions = ref([])
const paeDisplay = ref('')
const showPaeOptions = ref(false)
const municipioSearch = ref('')
const showMunicipioOptions = ref(false)
const estadoSearch = ref('')
const showEstadoOptions = ref(false)
const conceptoSearch = ref('')
const showConceptoOptions = ref(false)

const isGenerating = ref(false)
const generationProgress = ref(0)
const reportTask = ref(null)

// Computed
const yearsRange = computed(() => {
  const currentYear = new Date().getFullYear()
  const years = []
  for (let i = currentYear; i >= 2006; i--) {
    years.push(i)
  }
  return years
})

const filteredMunicipios = computed(() => {
  if (!municipioSearch.value) return filterOptions.municipios
  const search = municipioSearch.value.toLowerCase()
  return filterOptions.municipios.filter(m => m.nombre.toLowerCase().includes(search))
})

const filteredEstados = computed(() => {
  if (!estadoSearch.value) return filterOptions.estados
  const search = estadoSearch.value.toLowerCase()
  return filterOptions.estados.filter(e => e.toLowerCase().includes(search))
})

const filteredConceptos = computed(() => {
  if (!conceptoSearch.value) return filterOptions.conceptos_visita
  const search = conceptoSearch.value.toLowerCase()
  return filterOptions.conceptos_visita.filter(c => c.label.toLowerCase().includes(search))
})

// Methods
onMounted(async () => {
  try {
    const response = await axios.options('/api/reports/generate/')
    filterOptions.municipios = response.data.filter_options.municipios
    filterOptions.conceptos_visita = response.data.filter_options.conceptos_visita
    filterOptions.anios = response.data.filter_options.anios
    filterOptions.estados = response.data.filter_options.estados
    filterOptions.tiene_pae = response.data.filter_options.tiene_pae
  } catch (error) {
    console.error('Error cargando opciones:', error)
  }
})

// Institution Search
const onInstitutionInput = () => {
  if (institutionSearch.value.length < 3) {
    foundInstitutions.value = []
    return
  }
  // Debounce could be added here
}

const searchInstitutions = async () => {
  if (!institutionSearch.value) return
  try {
    const response = await axios.get('/api/etl/instituciones/', {
      params: { search: institutionSearch.value, limit: 5 }
    })
    foundInstitutions.value = response.data.results || []
  } catch (error) {
    console.error('Error buscando instituciones:', error)
  }
}

const selectInstitution = (inst) => {
  selectedFilters.instituciones = [inst.id]
  institutionSearch.value = inst.nombre
  foundInstitutions.value = []
}

// PAE Selection
const togglePaeOptions = () => {
  showPaeOptions.value = !showPaeOptions.value
}

const selectPae = (value) => {
  selectedFilters.tiene_pae = value
  if (value === true) paeDisplay.value = 'Con PAE'
  else if (value === false) paeDisplay.value = 'Sin PAE'
  else paeDisplay.value = 'Todos'
  showPaeOptions.value = false
}

// Municipio Selection
const selectMunicipio = (mun) => {
  selectedFilters.municipios = [mun.codigo]
  municipioSearch.value = mun.nombre
  showMunicipioOptions.value = false
}

// Estado Selection
const selectEstado = (est) => {
  selectedFilters.estados = [est]
  estadoSearch.value = est
  showEstadoOptions.value = false
}

// Concepto Selection
const selectConcepto = (con) => {
  selectedFilters.conceptos_visita = [con.value]
  conceptoSearch.value = con.label
  showConceptoOptions.value = false
}

// Generation
const generateReport = async (format) => {
  isGenerating.value = true
  generationProgress.value = 0
  reportTask.value = null

  // Prepare filters
  const filtersToSend = {
    ...selectedFilters,
    anios: selectedFilters.anio ? [selectedFilters.anio] : []
  }

  try {
    const response = await axios.post('/api/reports/generate/', {
      format: format,
      filters: filtersToSend
    })

    reportTask.value = {
      task_id: response.data.task_id,
      status: response.data.status
    }

    checkReportStatus(response.data.task_id)
  } catch (error) {
    console.error('Error:', error)
    isGenerating.value = false
    reportTask.value = { status: 'error', error: 'Error al iniciar generación' }
  }
}

const checkReportStatus = async (taskId, attempt = 0) => {
  if (attempt > 300) {
    reportTask.value.status = 'error'
    reportTask.value.error = 'Timeout'
    isGenerating.value = false
    return
  }

  try {
    const response = await axios.get(`/api/reports/status/${taskId}/`)
    reportTask.value = { ...reportTask.value, ...response.data }

    if (response.data.status === 'processing') {
      generationProgress.value = response.data.progress || 0
      setTimeout(() => checkReportStatus(taskId, attempt + 1), 1000)
    } else if (response.data.status === 'success') {
      isGenerating.value = false
      generationProgress.value = 100
      if (response.data.download_url) {
        window.location.href = response.data.download_url
      }
    } else {
      isGenerating.value = false
    }
  } catch (error) {
    setTimeout(() => checkReportStatus(taskId, attempt + 1), 2000)
  }
}

const closeStatus = () => {
  reportTask.value = null
  isGenerating.value = false
}
</script>

<style scoped>
.report-modal {
  background: white;
  padding: 20px;
  border-radius: 8px;
  max-width: 800px;
  margin: 0 auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.modal-title {
  color: #366092;
  margin-bottom: 20px;
  font-size: 24px;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 10px;
}

.fields-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.modal-field {
  position: relative;
}

.modal-label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 600;
  font-size: 14px;
}

.modal-input-group {
  display: flex;
  align-items: center;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
  background: #fff;
}

.modal-input, .modal-select {
  flex: 1;
  border: none;
  padding: 10px;
  font-size: 14px;
  outline: none;
  width: 100%;
}

.modal-search-btn {
  background: none;
  border: none;
  padding: 8px;
  cursor: pointer;
  color: #366092;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-search-btn:hover {
  background-color: #f5f5f5;
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-top: none;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.search-item {
  padding: 10px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}

.search-item:hover {
  background-color: #f0f8ff;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  margin-top: 20px;
  border-top: 1px solid #eee;
  padding-top: 20px;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 5px;
  transition: transform 0.2s;
}

.btn-icon:hover {
  transform: scale(1.1);
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-icon {
  width: 40px;
  height: 40px;
}

/* Status Overlay */
.status-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.status-content {
  background: white;
  padding: 30px;
  border-radius: 8px;
  text-align: center;
  min-width: 300px;
}

.progress-bar {
  width: 100%;
  height: 10px;
  background: #eee;
  border-radius: 5px;
  margin: 15px 0;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #366092;
  transition: width 0.3s ease;
}

.error-text {
  color: #dc3545;
}

.btn-close-status {
  margin-top: 15px;
  padding: 8px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>

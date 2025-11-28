<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo-section">
        <img src="/logo-uesvalle.png" alt="UesValle Logo" class="logo" />
        <h1 class="title">GeoVisor Instituciones Educativas UesValle</h1>
      </div>
    </div>
    
    <div class="header-center">
      <div class="search-container">
        <div class="search-wrapper">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Buscar Instituciones..."
            class="search-input"
            @input="handleInput"
            @focus="showResults = true"
            @blur="handleBlur"
          />
          <button class="search-button">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </button>
        </div>

        <!-- Resultados de búsqueda -->
        <div v-if="showResults && results.length > 0" class="search-results">
          <div 
            v-for="item in results" 
            :key="item.id" 
            class="search-item"
            @mousedown="selectResult(item)"
          >
            <div class="item-name">{{ item.nombre }}</div>
            <div class="item-codes">
              <span v-if="item.dane_ie_id" class="code-badge dane">DANE: {{ item.dane_ie_id }}</span>
              <span v-if="item.uesvalle_ie_id" class="code-badge ues">UES: {{ item.uesvalle_ie_id }}</span>
              <span v-if="!item.lat || !item.lon" class="code-badge no-coords">Sin coordenadas</span>
            </div>
          </div>
        </div>
        <div v-else-if="showResults && searchQuery.length > 2 && results.length === 0 && !loading" class="search-results empty">
          No se encontraron resultados
        </div>
      </div>
    </div>
    
    
  </header>

  <!-- Modal de detalles de institución (sin coordenadas) -->
  <Teleport to="body">
    <div v-if="showDetailModal" class="detail-modal-overlay" @click.self="closeDetailModal">
      <div class="detail-modal">
        <button @click="closeDetailModal" class="modal-close-btn">✕</button>
        
        <div v-if="loadingDetails" class="modal-loading">
          <div class="spinner"></div>
          <p>Cargando información...</p>
        </div>
        
        <div v-else-if="selectedInstitution" class="institution-details">
          <h2>{{ selectedInstitution.nombre }}</h2>
          
          <!-- Badge de advertencia sin coordenadas -->
          <div class="no-coords-warning">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>No se pudo determinar la ubicación de esta institución en el mapa, sin embargo esta registrada correctamente</span>
          </div>
          
          <!-- Concepto Actual con Badge de Color -->
          <div class="concepto-badge" :class="getConceptoClass(selectedInstitution.concepto_actual)">
            {{ getConceptoLabel(selectedInstitution.concepto_actual) }}
          </div>
          
          <!-- Identificadores -->
          <div class="info-section">
            <h3>Identificadores</h3>
            <p><strong>ID UESValle:</strong> {{ selectedInstitution.uesvalle_ie_id || 'No registrado' }}</p>
            <p><strong>Código DANE:</strong> {{ selectedInstitution.dane_ie_id || 'No registrado' }}</p>
          </div>
          
          <!-- Información General -->
          <div class="info-section">
            <h3>Información General</h3>
            <p><strong>Municipio:</strong> {{ getInstitutionMunicipio(selectedInstitution) }}</p>
            <p><strong>Dirección:</strong> {{ getInstitutionDireccion(selectedInstitution) }}</p>
            <p><strong>Teléfono:</strong> {{ getInstitutionTelefono(selectedInstitution) }}</p>
            <p><strong>Email:</strong> {{ getInstitutionEmail(selectedInstitution) }}</p>
          </div>
          
          <!-- Historial de Visitas -->
          <div class="info-section visitas-section" v-if="selectedInstitution.visitas && selectedInstitution.visitas.length > 0">
            <h3>Historial de Visitas ({{ selectedInstitution.total_visitas }})</h3>
            <div class="visitas-list">
              <div 
                v-for="(visita, index) in selectedInstitution.visitas" 
                :key="visita.id" 
                class="visita-item"
                :class="{ 'visita-actual': index === 0 }"
              >
                <div class="visita-header">
                  <span class="visita-fecha">{{ formatDate(visita.fechavisita) }}</span>
                  <span class="visita-concepto" :class="getConceptoClass(visita.conceptovisita)">
                    {{ visita.conceptovisita }}
                  </span>
                </div>
                <p class="visita-funcionario">
                  <strong>Funcionario:</strong> {{ visita.nombrefuncionario }} {{ visita.apellidofuncionario }}
                  <span class="codigo-funcionario">({{ visita.codigofuncionario }})</span>
                </p>
                
                <!-- Metadata de la visita (expandible) -->
                <details v-if="visita.metadata && Object.keys(visita.metadata).length > 0" class="metadata-details">
                  <summary>Ver detalles adicionales</summary>
                  <div class="metadata-grid">
                    <!-- Información del Establecimiento -->
                    <div class="metadata-group" v-if="hasEstablecimientoData(visita.metadata)">
                      <h4>Establecimiento</h4>
                      <p v-if="visita.metadata.direccionestablecimiento"><strong>Dirección:</strong> {{ visita.metadata.direccionestablecimiento }}</p>
                      <p v-if="visita.metadata.celular"><strong>Celular:</strong> {{ visita.metadata.celular }}</p>
                      <p v-if="visita.metadata.totaltrabajador"><strong>Trabajadores:</strong> {{ visita.metadata.totaltrabajador }}</p>
                      <p v-if="visita.metadata.numerosdocente"><strong>Docentes:</strong> {{ visita.metadata.numerosdocente }}</p>
                    </div>
                    
                    <!-- Información de Estudiantes -->
                    <div class="metadata-group" v-if="hasEstudiantesData(visita.metadata)">
                      <h4>Estudiantes</h4>
                      <p v-if="visita.metadata.estudianteshombre"><strong>Hombres:</strong> {{ visita.metadata.estudianteshombre }}</p>
                      <p v-if="visita.metadata.estudiantesmujer"><strong>Mujeres:</strong> {{ visita.metadata.estudiantesmujer }}</p>
                      <p v-if="visita.metadata.tienepae"><strong>Tiene PAE:</strong> {{ visita.metadata.tienepae }}</p>
                    </div>
                    
                    <!-- Ubicación -->
                    <div class="metadata-group" v-if="hasUbicacionData(visita.metadata)">
                      <h4>Ubicación</h4>
                      <p v-if="visita.metadata.nombremunicipio"><strong>Municipio:</strong> {{ visita.metadata.nombremunicipio }}</p>
                      <p v-if="visita.metadata.nombrecorregimiento"><strong>Corregimiento:</strong> {{ visita.metadata.nombrecorregimiento }}</p>
                      <p v-if="visita.metadata.nombrearo"><strong>ARO:</strong> {{ visita.metadata.nombrearo }}</p>
                    </div>
                    
                    <!-- Representante Legal -->
                    <div class="metadata-group" v-if="hasRepresentanteData(visita.metadata)">
                      <h4>Representante Legal</h4>
                      <p><strong>Nombre:</strong> {{ visita.metadata.nombrerepresentante }} {{ visita.metadata.apellidorepresentante }}</p>
                    </div>
                    
                    <!-- Resultado de la Visita -->
                    <div class="metadata-group" v-if="hasResultadoData(visita.metadata)">
                      <h4>Resultado</h4>
                      <p v-if="visita.metadata.cumplimiento"><strong>Cumplimiento:</strong> {{ visita.metadata.cumplimiento }}%</p>
                      <p v-if="visita.metadata.plazo"><strong>Plazo:</strong> {{ visita.metadata.plazo }} días</p>
                      <p v-if="visita.metadata.fecha_cargue"><strong>Fecha cargue:</strong> {{ visita.metadata.fecha_cargue }}</p>
                    </div>
                    
                    <!-- Usuario que cargó -->
                    <div class="metadata-group" v-if="visita.metadata.nombreusuario">
                      <h4>Cargado por</h4>
                      <p>{{ visita.metadata.nombreusuario }}</p>
                    </div>
                  </div>
                  
                  <!-- Requerimientos/Observaciones -->
                  <div v-if="visita.requerimientos || visita.observacion" class="observaciones-section">
                    <h4 v-if="visita.requerimientos">Requerimientos</h4>
                    <p v-if="visita.requerimientos" class="observacion-text">{{ visita.requerimientos }}</p>
                    <h4 v-if="visita.observacion">Observaciones</h4>
                    <p v-if="visita.observacion" class="observacion-text">{{ visita.observacion }}</p>
                  </div>
                </details>
              </div>
            </div>
          </div>
          
          <!-- Sedes de la institución -->
          <div class="info-section" v-if="selectedInstitution.sedes && selectedInstitution.sedes.length > 0">
            <h3>Sedes ({{ selectedInstitution.sedes?.length || 0 }})</h3>
            <ul class="sedes-list">
              <li v-for="sede in selectedInstitution.sedes" :key="sede.id" class="sede-item">
                <strong>{{ sede.nombre }}</strong>
                <p>{{ sede.direccion }}</p>
                <p v-if="sede.lat && sede.lon" class="coords">{{ sede.lat?.toFixed(6) }}, {{ sede.lon?.toFixed(6) }}</p>
              </li>
            </ul>
          </div>
        </div>
        
        <div v-else class="modal-error">
          <p>No se pudo cargar la información de la institución</p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMapControls } from '../shared/composables/useMapControls'

const { selectInstitution } = useMapControls()

const searchQuery = ref('')
const results = ref<any[]>([])
const showResults = ref(false)
const loading = ref(false)
let debounceTimer: any = null

// Modal de detalles
const showDetailModal = ref(false)
const loadingDetails = ref(false)
const selectedInstitution = ref<any>(null)

const handleInput = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  
  if (searchQuery.value.length < 3) {
    results.value = []
    return
  }

  loading.value = true
  debounceTimer = setTimeout(async () => {
    try {
      const response = await fetch(`/api/etl/map/search/?q=${encodeURIComponent(searchQuery.value)}`)
      const data = await response.json()
      results.value = data
    } catch (error) {
      console.error('Error searching:', error)
      results.value = []
    } finally {
      loading.value = false
      showResults.value = true
    }
  }, 300)
}

const handleBlur = () => {
  // Delay hiding results to allow click event to fire
  setTimeout(() => {
    showResults.value = false
  }, 200)
}

// Función para obtener detalles de la institución
async function fetchInstitutionDetails(institucionId: string) {
  try {
    loadingDetails.value = true
    const response = await fetch(`/api/etl/map/institucion/${institucionId}/`)
    const data = await response.json()
    
    if (data.status === 'success') {
      selectedInstitution.value = data.institucion
      console.log('✓ Detalles de institución cargados:', data.institucion)
    } else {
      selectedInstitution.value = null
    }
  } catch (error) {
    console.error('Error obteniendo detalles:', error)
    selectedInstitution.value = null
  } finally {
    loadingDetails.value = false
  }
}

const selectResult = (item: any) => {
  console.log('Selected result:', item)
  searchQuery.value = item.nombre
  showResults.value = false
  
  if (item.lat && item.lon) {
    console.log('Triggering selection with coords:', item.lat, item.lon)
    selectInstitution(item.id, Number(item.lat), Number(item.lon))
  } else {
    // Mostrar modal con detalles para instituciones sin coordenadas
    console.log('Opening detail modal for item without coordinates:', item)
    showDetailModal.value = true
    fetchInstitutionDetails(item.id)
  }
}

// Cerrar modal de detalles
function closeDetailModal() {
  showDetailModal.value = false
  selectedInstitution.value = null
}

// ===== FUNCIONES HELPER =====
function getConceptoClass(concepto: string | null): string {
  if (!concepto) return 'concepto-none'
  switch (concepto.toUpperCase()) {
    case 'F': return 'concepto-favorable'
    case 'D': return 'concepto-desfavorable'
    case 'FCR': return 'concepto-fcr'
    default: return 'concepto-none'
  }
}

function getConceptoLabel(concepto: string | null): string {
  if (!concepto) return 'Sin concepto'
  switch (concepto.toUpperCase()) {
    case 'F': return 'Favorable'
    case 'D': return 'Desfavorable'
    case 'FCR': return 'Favorable con Requerimientos'
    default: return concepto
  }
}

function formatDate(dateString: string | null): string {
  if (!dateString) return 'N/A'
  const parts = dateString.split('T')[0].split('-')
  const date = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]))
  return date.toLocaleDateString('es-CO', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// Funciones para verificar si hay datos en cada grupo de metadata
function hasEstablecimientoData(metadata: any): boolean {
  return metadata && (metadata.direccionestablecimiento || metadata.celular || metadata.totaltrabajador || metadata.numerosdocente)
}

function hasEstudiantesData(metadata: any): boolean {
  return metadata && (metadata.estudianteshombre || metadata.estudiantesmujer || metadata.tienepae)
}

function hasUbicacionData(metadata: any): boolean {
  return metadata && (metadata.nombremunicipio || metadata.nombrecorregimiento || metadata.nombrearo)
}

function hasRepresentanteData(metadata: any): boolean {
  return metadata && (metadata.nombrerepresentante || metadata.apellidorepresentante)
}

function hasResultadoData(metadata: any): boolean {
  return metadata && (metadata.cumplimiento || metadata.plazo || metadata.fecha_cargue)
}

// Helper functions to extract institution info from latest visit metadata
function getLatestVisitMetadata(institution: any): any {
  if (!institution || !institution.visitas || institution.visitas.length === 0) return null
  return institution.visitas[0]?.metadata || null
}

function getInstitutionMunicipio(institution: any): string {
  const metadata = getLatestVisitMetadata(institution)
  return metadata?.nombremunicipio || institution?.codigo_municipio || 'N/A'
}

function getInstitutionDireccion(institution: any): string {
  const metadata = getLatestVisitMetadata(institution)
  return metadata?.direccionestablecimiento || institution?.direccion || 'N/A'
}

function getInstitutionTelefono(institution: any): string {
  const metadata = getLatestVisitMetadata(institution)
  return metadata?.celular || institution?.telefono || 'N/A'
}

function getInstitutionEmail(institution: any): string {
  return institution?.email || 'N/A'
}
</script>

<style scoped>
.app-header {
  height: 70px;
  background: #262626;
 
  display: flex;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  position: relative;
}

.header-left {
  flex: 0 0 auto;
  min-width: 300px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
  
}

.logo {
  height: 45px;
  width: auto;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
  white-space: nowrap;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 0 40px;
}

.search-container {
  position: relative;
  width: 100%;
  max-width: 500px;
}

.search-wrapper {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
}

.search-input {
  width: 100%;
  height: 40px;
  padding: 0 45px 0 15px;
  border: 1px solid #444;
  border-radius: 20px;
  background: #333;
  color: white;
  font-size: 14px;
  transition: all 0.3s ease;
}

.search-input:focus {
  outline: none;
  background: #404040;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.search-button {
  position: absolute;
  right: 5px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #aaa;
  cursor: pointer;
  padding: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: color 0.3s;
}

.search-button:hover {
  color: white;
  background: rgba(255,255,255,0.1);
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border-radius: 8px;
  margin-top: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  max-height: 300px;
  overflow-y: auto;
  z-index: 1001;
}

.search-item {
  padding: 10px 15px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  transition: background 0.2s;
}

.search-item:last-child {
  border-bottom: none;
}

.search-item:hover {
  background: #f5f5f5;
}

.item-name {
  font-weight: 600;
  color: #333;
  font-size: 14px;
  margin-bottom: 4px;
}

.item-codes {
  display: flex;
  gap: 8px;
  font-size: 11px;
}

.code-badge {
  padding: 2px 6px;
  border-radius: 4px;
  background: #eee;
  color: #666;
}

.code-badge.dane {
  background: #e3f2fd;
  color: #1565c0;
}

.code-badge.ues {
  background: #e8f5e9;
  color: #2e7d32;
}

.search-results.empty {
  padding: 15px;
  text-align: center;
  color: #666;
  font-size: 13px;
}

.header-right {
  flex: 0 0 auto;
  min-width: 120px;
}

.header-icons {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}

.header-icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: background-color 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-icon-btn:hover {
  background: #f0f0f0;
}

.header-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

/* Badge sin coordenadas en resultados de búsqueda */
.code-badge.no-coords {
  background: #fff3e0;
  color: #e65100;
  font-weight: 500;
}

/* ===== MODAL DE DETALLES ===== */
.detail-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.detail-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  position: relative;
  animation: slideUp 0.25s ease;
  padding: 24px;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  background: #f5f5f5;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #666;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.modal-close-btn:hover {
  background: #e0e0e0;
  color: #333;
}

.modal-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f0f0f0;
  border-top-color: #663399;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.modal-error {
  text-align: center;
  padding: 40px;
  color: #d32f2f;
}

/* Advertencia sin coordenadas */
.no-coords-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #fff3e0;
  border-radius: 8px;
  margin-bottom: 16px;
  color: #e65100;
  font-size: 13px;
}

.no-coords-warning svg {
  flex-shrink: 0;
}

/* Estilos del contenido del modal */
.institution-details h2 {
  margin: 0 0 12px;
  color: #333;
  font-size: 18px;
  padding-right: 40px;
}

.concepto-badge {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 15px;
}

.concepto-favorable {
  background: #d4edda;
  color: #155724;
}

.concepto-desfavorable {
  background: #f8d7da;
  color: #721c24;
}

.concepto-fcr {
  background: #fff3cd;
  color: #856404;
}

.concepto-none {
  background: #e2e3e5;
  color: #6c757d;
}

.info-section {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.info-section h3 {
  font-size: 14px;
  color: #333;
  margin: 0 0 10px;
  font-weight: 600;
}

.info-section h4 {
  font-size: 12px;
  color: #555;
  margin: 8px 0 4px;
  font-weight: 600;
}

.info-section p {
  margin: 8px 0;
  font-size: 13px;
  color: #666;
}

/* Visitas */
.visitas-list {
  max-height: 250px;
  overflow-y: auto;
}

.visita-item {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
  border-left: 3px solid #ccc;
}

.visita-item.visita-actual {
  border-left-color: #663399;
  background: #f3f0f7;
}

.visita-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.visita-fecha {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.visita-concepto {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.visita-funcionario {
  font-size: 12px;
  color: #555;
  margin: 4px 0;
}

.codigo-funcionario {
  font-size: 10px;
  color: #999;
}

/* Metadata expandible */
.metadata-details {
  margin-top: 10px;
}

.metadata-details summary {
  font-size: 11px;
  color: #663399;
  cursor: pointer;
  font-weight: 500;
}

.metadata-details summary:hover {
  text-decoration: underline;
}

.metadata-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
  padding: 10px;
  background: #fff;
  border-radius: 4px;
}

.metadata-group {
  font-size: 11px;
}

.metadata-group h4 {
  font-size: 11px;
  color: #663399;
  margin: 0 0 4px;
  border-bottom: 1px solid #eee;
  padding-bottom: 2px;
}

.metadata-group p {
  margin: 2px 0;
  font-size: 11px;
  color: #555;
}

.observaciones-section {
  margin-top: 10px;
  padding: 10px;
  background: #fff8e1;
  border-radius: 4px;
}

.observaciones-section h4 {
  font-size: 11px;
  color: #ff6f00;
  margin: 0 0 4px;
}

.observacion-text {
  font-size: 11px;
  color: #666;
  white-space: pre-wrap;
  line-height: 1.4;
}

/* Sedes */
.sedes-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sede-item {
  background: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 8px;
  font-size: 12px;
}

.sede-item strong {
  display: block;
  color: #333;
  margin-bottom: 4px;
}

.sede-item p {
  margin: 4px 0;
  color: #666;
}

.coords {
  font-family: monospace;
  font-size: 11px;
  color: #999;
}
</style>
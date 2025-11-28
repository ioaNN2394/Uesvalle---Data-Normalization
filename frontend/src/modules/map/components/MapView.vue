<template>
  <div class="map-container">
    <!-- Mapa Leaflet -->
    <div id="map" ref="mapContainer" class="map"></div>
    
    <!-- Panel de información (cuando se hace click en un marcador) -->
    <div v-if="selectedInstitution" class="info-panel">
      <button @click="closeInfo" class="close-btn">✕</button>
      <div class="institution-info">
        <h2>{{ selectedInstitution.nombre }}</h2>
        
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
          <p><strong>Municipio:</strong> {{ selectedInstitution.codigo_municipio }}</p>
          <p><strong>Dirección:</strong> {{ selectedInstitution.direccion || 'N/A' }}</p>
          <p><strong>Teléfono:</strong> {{ selectedInstitution.telefono || 'N/A' }}</p>
          <p><strong>Email:</strong> {{ selectedInstitution.email || 'N/A' }}</p>
          <p v-if="selectedInstitution.lat"><strong>Coordenadas:</strong> {{ selectedInstitution.lat.toFixed(6) }}, {{ selectedInstitution.lon.toFixed(6) }}</p>
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
              <p class="coords">{{ sede.lat?.toFixed(6) }}, {{ sede.lon?.toFixed(6) }}</p>
            </li>
          </ul>
        </div>
      </div>
    </div>
    
    <!-- Visualizador de coordenadas -->
    <div class="coords-display">
      Lat: {{ mouseCoords.lat.toFixed(6) }} | Lon: {{ mouseCoords.lon.toFixed(6) }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useMapControls } from '../../../shared/composables/useMapControls'

const { zoomAction, filterState, selectedInstitutionAction } = useMapControls()

const mapContainer = ref<HTMLDivElement>()
let map: any = null
let markers: any[] = []

const mouseCoords = ref({ lat: 0, lon: 0 })
const selectedInstitution = ref<any>(null)
const institutionsData = ref<any[]>([])

// ===== API CALLS =====
async function fetchMapMarkers() {
  try {
    // Construir query params
    const params = new URLSearchParams()
    
    if (filterState.conceptos && filterState.conceptos.length > 0) {
      // Enviar como string separado por comas para que el backend lo procese con split(',')
      params.append('conceptos', filterState.conceptos.join(','))
    }
    
    if (filterState.fechaInicio) {
      params.append('fecha_inicio', filterState.fechaInicio)
    }
    
    if (filterState.fechaFin) {
      params.append('fecha_fin', filterState.fechaFin)
    }

    const queryString = params.toString()
    const url = `/api/etl/map/markers/${queryString ? '?' + queryString : ''}`
    
    console.log('Fetching markers with URL:', url)

    const response = await fetch(url)
    const data = await response.json()
    
    if (data.status === 'success') {
      institutionsData.value = data.data
      console.log(`✓ Cargados ${data.count} marcadores`)
      addMarkersToMap()
    }
  } catch (error) {
    console.error('Error obteniendo marcadores:', error)
  }
}

async function fetchInstitutionDetails(institucionId: string) {
  try {
    console.log('Fetching details for:', institucionId)
    const response = await fetch(`/api/etl/map/institucion/${institucionId}/`)
    const data = await response.json()
    
    if (data.status === 'success') {
      selectedInstitution.value = data.institucion
      console.log('✓ Detalles de institución cargados:', data.institucion)
    }
  } catch (error) {
    console.error('Error obteniendo detalles:', error)
  }
}

// ===== WATCHERS =====
watch(zoomAction, (newAction) => {
  if (!map || !newAction) return
  
  if (newAction === 'in') {
    map.zoomIn()
  } else if (newAction === 'out') {
    map.zoomOut()
  } else if (newAction === 'reset') {
    map.setView([3.8, -76.3], 9)
  }
})

watch(filterState, () => {
  console.log('Filtros cambiaron, recargando mapa...')
  fetchMapMarkers()
}, { deep: true })

watch(selectedInstitutionAction, (action) => {
  if (!map) {
    console.warn('Map not initialized when selection triggered')
    return
  }
  if (!action) return
  
  console.log('Centering map on:', action)
  try {
    map.flyTo([action.lat, action.lon], 15, {
      duration: 1.5
    })
    fetchInstitutionDetails(action.id)
  } catch (e) {
    console.error('Error flying to location:', e)
  }
})

// ===== INICIALIZACIÓN DEL MAPA =====
async function initMap() {
  if (!mapContainer.value) return
  
  try {
    // Importa Leaflet dinámicamente
    const L = (await import('leaflet')).default
    
    // Importa estilos
    await import('leaflet/dist/leaflet.css')
    
    // Fix para los iconos de Leaflet
    delete (L.Icon.Default.prototype as any)._getIconUrl
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
      iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    })
    
    // Crea el mapa
    map = L.map(mapContainer.value).setView([3.8, -76.3], 9)
    
    // Capa base (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19
    }).addTo(map)
    
    // Control de escala
    L.control.scale().addTo(map)
    
    // Actualiza coordenadas del mouse
    map.on('mousemove', (e: any) => {
      mouseCoords.value = {
        lat: e.latlng.lat,
        lon: e.latlng.lng
      }
    })
    
    // Carga los marcadores
    await fetchMapMarkers()
  } catch (error) {
    console.error('Error inicializando mapa:', error)
  }
}

// ===== AGREGAR MARCADORES AL MAPA =====
async function addMarkersToMap() {
  // Esperar a que Leaflet esté disponible
  const L = await import('leaflet').then(m => m.default)
  
  if (!map) return
  
  // Elimina marcadores anteriores
  markers.forEach((marker: any) => {
    map.removeLayer(marker)
  })
  markers = []
  
  // Ícono personalizado (puntos de color vino/morado)
  const customIcon = L.divIcon({
    className: 'custom-marker',
    html: '<div class="marker-dot"></div>',
    iconSize: [10, 10],
    iconAnchor: [5, 5],
    popupAnchor: [0, -5]
  })
  
  // Crea un marcador para cada institución
  institutionsData.value.forEach((item: any) => {
    // Validar coordenadas antes de crear marcador
    if (item.lat != null && item.lon != null && !isNaN(item.lat) && !isNaN(item.lon)) {
      const marker = L.marker([item.lat, item.lon], { icon: customIcon })
        .addTo(map)
        .bindPopup(
          `<div class="marker-popup">
            <strong>${item.institucion}</strong><br/>
            <button onclick="window.mapClickMarker('${item.institucion_id}')">Ver Detalles</button>
          </div>`
        )
      
      markers.push(marker)
    }
  })
  
  console.log(`✓ ${markers.length} marcadores agregados al mapa`)
}

// ===== MANEJADORES DE EVENTOS =====
function closeInfo() {
  selectedInstitution.value = null
}

// Global function para click en popup
;(window as any).mapClickMarker = (institucionId: string) => {
  fetchInstitutionDetails(institucionId)
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
  // Parsear la fecha como local (no UTC) para evitar desfase de zona horaria
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

// ===== CICLO DE VIDA =====
onMounted(async () => {
  console.log('📍 Inicializando mapa...')
  await initMap()
})

onUnmounted(() => {
  if (map) {
    map.remove()
  }
})
</script>

<style scoped>
.map-container {
  position: relative;
  width: 100%;
  height: 100%;
}

#map {
  width: 100%;
  height: 100%;
  z-index: 1;
}

.coords-display {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 10;
  font-family: monospace;
}

.info-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 350px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 100;
  max-height: 70vh;
  overflow-y: auto;
  padding: 20px;
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.institution-info h2 {
  margin: 0 0 15px;
  color: #333;
  font-size: 18px;
}

.institution-info p {
  margin: 8px 0;
  font-size: 13px;
  color: #666;
}

.sedes-list {
  margin-top: 20px;
  border-top: 1px solid #eee;
  padding-top: 15px;
}

.sedes-list h3 {
  font-size: 14px;
  margin: 0 0 10px;
  color: #333;
}

.sedes-list ul {
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

/* === Estilos para el nuevo panel de detalles === */
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

/* Visitas */
.visitas-list {
  max-height: 300px;
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
</style>

<style>
/* Estilos globales para Leaflet (sin scoped) */
.custom-marker {
  background: transparent !important;
  border: none !important;
}

.marker-dot {
  width: 8px;
  height: 8px;
  background-color: #663399;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.marker-popup {
  font-size: 12px;
  text-align: center;
}

.marker-popup button {
  background: #663399;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  margin-top: 8px;
}

.marker-popup button:hover {
  background: #553388;
}

.leaflet-popup-content-wrapper {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.leaflet-container {
  background: #f0f8ff;
}
</style>
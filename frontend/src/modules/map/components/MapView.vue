<template>
  <div class="map-container">
    <!-- Mapa Leaflet -->
    <div id="map" ref="mapContainer" class="map"></div>
    
    <!-- Panel de información (cuando se hace click en un marcador) -->
    <div v-if="selectedInstitution" class="info-panel">
      <button @click="closeInfo" class="close-btn">✕</button>
      <div class="institution-info">
        <h2>{{ selectedInstitution.nombre }}</h2>
        <p><strong>DANE:</strong> {{ selectedInstitution.dane_ie_id }}</p>
        <p><strong>Municipio:</strong> {{ selectedInstitution.codigo_municipio }}</p>
        <p><strong>Dirección:</strong> {{ selectedInstitution.direccion }}</p>
        <p><strong>Teléfono:</strong> {{ selectedInstitution.telefono || 'N/A' }}</p>
        <p><strong>Email:</strong> {{ selectedInstitution.email || 'N/A' }}</p>
        <p><strong>Estado:</strong> {{ selectedInstitution.estado }}</p>
        <p v-if="selectedInstitution.lat"><strong>Coordenadas:</strong> {{ selectedInstitution.lat.toFixed(6) }}, {{ selectedInstitution.lon.toFixed(6) }}</p>
        
        <!-- Sedes de la institución -->
        <div class="sedes-list" v-if="selectedInstitution.sedes && selectedInstitution.sedes.length > 0">
          <h3>Sedes ({{ selectedInstitution.sedes?.length || 0 }})</h3>
          <ul>
            <li v-for="sede in selectedInstitution.sedes" :key="sede.id" class="sede-item">
              <strong>{{ sede.nombre }}</strong>
              <p>{{ sede.direccion }}</p>
              <p class="coords">{{ sede.lat.toFixed(6) }}, {{ sede.lon.toFixed(6) }}</p>
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
</style>

<style>
/* Estilos globales para Leaflet */
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
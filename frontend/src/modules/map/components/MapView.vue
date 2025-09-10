<template>
  <div class="map-view">
    <div ref="mapContainer" class="map-container"></div>
    <div class="map-coordinates">
      {{ coordinates }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix para los iconos de Leaflet en Vite
import icon from 'leaflet/dist/images/marker-icon.png'
import iconShadow from 'leaflet/dist/images/marker-shadow.png'

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
})

L.Marker.prototype.options.icon = DefaultIcon

// Interfaces TypeScript
interface Institution {
  id: number
  name: string
  lat: number
  lng: number
  type: string
}

// Refs
const mapContainer = ref<HTMLDivElement>()
const coordinates = ref<string>('-75.919, 3.528 Grados')
let map: L.Map | null = null

// Datos de ejemplo de instituciones educativas en Valle del Cauca
const mockInstitutions: Institution[] = [
  { id: 1, name: 'IE San José', lat: 3.4516, lng: -76.5320, type: 'Público' },
  { id: 2, name: 'Colegio La Salle', lat: 3.4372, lng: -76.5225, type: 'Privado' },
  { id: 3, name: 'IE Santa Librada', lat: 4.0892, lng: -76.1958, type: 'Público' },
  { id: 4, name: 'Colegio Bolivariano', lat: 3.8914, lng: -76.2929, type: 'Público' },
  { id: 5, name: 'IE Ciudad de Cali', lat: 3.4372, lng: -76.5225, type: 'Público' },
  { id: 6, name: 'Colegio San Juan Bosco', lat: 4.0892, lng: -76.1958, type: 'Privado' },
]

const initMap = (): void => {
  if (!mapContainer.value) return

  // Crear el mapa centrado en Valle del Cauca
  map = L.map(mapContainer.value).setView([3.8, -76.3], 8)

  // Agregar capa base
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'Data © OpenStreetMap contributors'
  }).addTo(map)

  // Agregar marcadores de instituciones
  mockInstitutions.forEach((institution: Institution) => {
    const marker = L.marker([institution.lat, institution.lng])
      .bindPopup(`
        <div class="popup-content">
          <h3>${institution.name}</h3>
          <p><strong>Tipo:</strong> ${institution.type}</p>
          <p><strong>Coordenadas:</strong> ${institution.lat.toFixed(4)}, ${institution.lng.toFixed(4)}</p>
        </div>
      `)
    
    marker.addTo(map)
  })

  // Actualizar coordenadas al mover el cursor
  map.on('mousemove', (e: L.LeafletMouseEvent) => {
    coordinates.value = `${e.latlng.lng.toFixed(3)}, ${e.latlng.lat.toFixed(3)} Grados`
  })

  // Agregar control de escala
  L.control.scale({
    position: 'bottomleft',
    metric: true,
    imperial: false
  }).addTo(map)
}

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (map) {
    map.remove()
  }
})
</script>

<style scoped>
.map-view {
  height: 100%;
  position: relative;
}

.map-container {
  height: 100%;
  width: 100%;
}

.map-coordinates {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background: rgba(255, 255, 255, 0.8);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  z-index: 1000;
  border: 1px solid #ddd;
}
</style>

<style>
.popup-content h3 {
  margin: 0 0 8px 0;
  color: #2c3e50;
}

.popup-content p {
  margin: 4px 0;
  font-size: 13px;
}
</style>

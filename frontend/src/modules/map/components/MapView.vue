<template>
  <div class="map-view">
    <div ref="mapContainer" class="map-container"></div>
    <div class="map-coordinates">
      {{ coordinates }}
    </div>
    <div class="map-scale"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'

const mapContainer = ref<HTMLDivElement>()
const coordinates = ref('-75.919, 3.528 Grados')
let map: any = null

// Datos de ejemplo de instituciones educativas del Valle del Cauca
const mockInstitutions = [
  { id: 1, name: 'IE San José de Cali', lat: 3.4516, lng: -76.5320, type: 'Público', municipio: 'Cali' },
  { id: 2, name: 'Colegio La Salle Cali', lat: 3.4372, lng: -76.5225, type: 'Privado', municipio: 'Cali' },
  { id: 3, name: 'IE Santa Librada Tuluá', lat: 4.0892, lng: -76.1958, type: 'Público', municipio: 'Tuluá' },
  { id: 4, name: 'Colegio Bolivariano Palmira', lat: 3.5394, lng: -76.3037, type: 'Público', municipio: 'Palmira' },
  { id: 5, name: 'IE José María Córdoba Buenaventura', lat: 3.8833, lng: -77.0167, type: 'Público', municipio: 'Buenaventura' },
  { id: 6, name: 'Colegio San Pedro Claver Buga', lat: 3.9019, lng: -76.2929, type: 'Privado', municipio: 'Buga' },
  // Agregar más instituciones para simular densidad como en la imagen
  ...Array.from({ length: 200 }, (_, i) => ({
    id: i + 7,
    name: `Institución Educativa ${i + 1}`,
    lat: 3.2 + Math.random() * 1.2,
    lng: -77.2 + Math.random() * 1.5,
    type: Math.random() > 0.5 ? 'Público' : 'Privado',
    municipio: ['Cali', 'Palmira', 'Tuluá', 'Buga', 'Buenaventura', 'Cartago'][Math.floor(Math.random() * 6)]
  }))
]

const initMap = async () => {
  if (!mapContainer.value) return

  try {
    // Importar Leaflet dinámicamente
    const L = await import('leaflet')
    await import('leaflet/dist/leaflet.css')

    // Fix para los iconos de Leaflet
    delete (L.Icon.Default.prototype as any)._getIconUrl
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
      iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    })

    // Crear el mapa centrado en Valle del Cauca
    map = L.map(mapContainer.value, {
      center: [3.8, -76.3],
      zoom: 8,
      zoomControl: false, // Remover controles por defecto
      attributionControl: false // Remover atribución por defecto
    })

    // Agregar capa base similar a la imagen
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: ''
    }).addTo(map)

    // Crear icono personalizado para las instituciones (color vino como en la imagen)
    const customIcon = L.divIcon({
      className: 'custom-marker',
      html: '<div class="marker-dot"></div>',
      iconSize: [8, 8],
      iconAnchor: [4, 4]
    })

    // Agregar marcadores de instituciones
    mockInstitutions.forEach(institution => {
      const marker = L.marker([institution.lat, institution.lng], { icon: customIcon })
        .bindPopup(`
          <div class="popup-content">
            <h3>${institution.name}</h3>
            <p><strong>Tipo:</strong> ${institution.type}</p>
            <p><strong>Municipio:</strong> ${institution.municipio}</p>
            <p><strong>Coordenadas:</strong> ${institution.lat.toFixed(4)}, ${institution.lng.toFixed(4)}</p>
          </div>
        `)
      
      marker.addTo(map)
    })

    // Actualizar coordenadas al mover el cursor
    map.on('mousemove', (e: any) => {
      coordinates.value = `${e.latlng.lng.toFixed(3)}, ${e.latlng.lat.toFixed(3)} Grados`
    })

    // Agregar control de escala
    L.control.scale({
      position: 'bottomleft',
      metric: true,
      imperial: false
    }).addTo(map)

    // Forzar resize del mapa
    nextTick(() => {
      if (map) {
        map.invalidateSize()
      }
    })

  } catch (error) {
    console.error('Error initializing map:', error)
  }
}

onMounted(() => {
  nextTick(() => {
    initMap()
  })
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
  width: 100%;
  position: relative;
  overflow: hidden;
}

.map-container {
  height: 100%;
  width: 100%;
  background: #f0f8ff;
}

.map-coordinates {
  position: absolute;
  bottom: 30px;
  left: 15px;
  background: rgba(255, 255, 255, 0.9);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #333;
  border: 1px solid rgba(0, 0, 0, 0.1);
  z-index: 1000;
}

.map-scale {
  position: absolute;
  bottom: 60px;
  left: 15px;
  z-index: 1000;
}
</style>

<style>
/* Estilos globales para el mapa */
.custom-marker {
  background: transparent !important;
  border: none !important;
}

.marker-dot {
  width: 6px;
  height: 6px;
  background-color: #8B1538;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.8);
}

.leaflet-popup-content-wrapper {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.popup-content h3 {
  margin: 0 0 8px 0;
  color: #2c3e50;
  font-size: 14px;
}

.popup-content p {
  margin: 4px 0;
  font-size: 12px;
  color: #666;
}

.leaflet-container {
  background: #f0f8ff;
}

.leaflet-control-scale-line {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  color: #333;
}
</style>
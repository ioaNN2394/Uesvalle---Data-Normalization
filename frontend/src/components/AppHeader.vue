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
            </div>
          </div>
        </div>
        <div v-else-if="showResults && searchQuery.length > 2 && results.length === 0 && !loading" class="search-results empty">
          No se encontraron resultados
        </div>
      </div>
    </div>
    
    
  </header>
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

const selectResult = (item: any) => {
  console.log('Selected result:', item)
  searchQuery.value = item.nombre
  showResults.value = false
  
  if (item.lat && item.lon) {
    console.log('Triggering selection with coords:', item.lat, item.lon)
    selectInstitution(item.id, Number(item.lat), Number(item.lon))
  } else {
    console.warn('Selected item has no coordinates:', item)
  }
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
</style>
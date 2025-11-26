<template>
  <aside class="sidebar">
    <div class="tool-group">
      <button 
        v-for="tool in tools" 
        :key="tool.id"
        @click="handleToolClick(tool.id)"
        :class="['tool-button', { active: activeTool === tool.id }]"
        :title="tool.tooltip"
      >
        <span v-html="iconComponents[tool.icon as keyof typeof iconComponents]"></span>
      </button>
    </div>
    
    <!-- Panel de Filtros -->
    <div v-if="activeTool === 'filter'" class="filter-panel">
      <h3>Filtros</h3>
      
      <div class="filter-section">
        <h4>Concepto Visita</h4>
        <div class="checkbox-group">
          <label><input type="checkbox" value="F" v-model="selectedConcepts"> Favorable (F)</label>
          <label><input type="checkbox" value="D" v-model="selectedConcepts"> Desfavorable (D)</label>
          <label><input type="checkbox" value="FCR" v-model="selectedConcepts"> Favorable con Rec. (FCR)</label>
        </div>
      </div>
      
      <div class="filter-section">
        <h4>Fecha de Visita</h4>
        <div class="date-group">
          <label>Desde:</label>
          <input type="date" v-model="startDate">
          <label>Hasta:</label>
          <input type="date" v-model="endDate">
        </div>
      </div>
      
      <div class="filter-actions">
        <button @click="applyFiltersHandler" class="btn-apply">Aplicar Filtros</button>
        <button @click="clearFiltersHandler" class="btn-clear">Borrar Filtros</button>
      </div>
    </div>
    
    <div class="navbar-icons">
      <button 
        ref="etlButtonRef"
        class="navbar-icon-btn" 
        title="Actualización ETL" 
        @click="showETLModal = true"
        aria-label="Abrir diálogo de carga de archivos para actualizar ETL"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
      </button>
      <button class="navbar-icon-btn notification-btn" title="Notificaciones" @click="toggleNotifications">
        <img src="/campana.png" alt="Notificaciones" class="navbar-icon" />
        <span v-if="unreadCount > 0" class="notification-badge">{{ unreadCount }}</span>
      </button>
      <button class="navbar-icon-btn" title="Reportes" @click="showReportModal = true">
        <img src="/reporte.png" alt="Reportes" class="navbar-icon" />
      </button>
    </div>

    <!-- Panel de Notificaciones -->
    <div v-if="showNotifications" class="notification-panel">
      <div class="notification-header">
        <h3>Notificaciones</h3>
        <button @click="showNotifications = false" class="close-btn">✕</button>
      </div>
      <div v-if="loadingNotifications" class="loading-state">
        Cargando...
      </div>
      <div v-else-if="notifications.length === 0" class="empty-state">
        No hay notificaciones nuevas
      </div>
      <div v-else class="notification-list">
        <div 
          v-for="notif in notifications" 
          :key="notif.id" 
          class="notification-item"
          :class="{ unread: !notif.is_read }"
          @click="markAsRead(notif)"
        >
          <div class="notif-title">{{ notif.institucion_nombre }}</div>
          <div class="notif-codes">
            <span>DANE: {{ notif.institucion_dane }}</span>
            <span>UES: {{ notif.institucion_ues }}</span>
          </div>
          <div class="notif-change">
            <span class="concept old">{{ notif.old_concept || 'N/A' }}</span>
            <span class="arrow">→</span>
            <span class="concept new">{{ notif.new_concept }}</span>
          </div>
          <div class="notif-date">{{ formatDate(notif.created_at) }}</div>
        </div>
      </div>
    </div>

    <ETLUploadModal 
      :is-open="showETLModal" 
      @close="handleETLModalClose"
    />
    <ReportModal v-if="showReportModal" @close="showReportModal = false" />
  </aside>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ReportModal from '../modules/reports/components/ReportModal.vue'
import ETLUploadModal from '../modules/etl/components/ETLUploadModal.vue'
import { useMapControls } from '../shared/composables/useMapControls'

const { triggerZoomIn, triggerZoomOut, triggerResetView, applyFilters, clearFilters } = useMapControls()

interface Tool {
  id: string
  icon: string
  tooltip: string
}

const activeTool = ref<string>('')
const showReportModal = ref(false)
const showETLModal = ref(false)
const etlButtonRef = ref<HTMLButtonElement | null>(null)

// Notificaciones
const showNotifications = ref(false)
const notifications = ref<any[]>([])
const unreadCount = ref(0)
const loadingNotifications = ref(false)

// Estado local de filtros
const selectedConcepts = ref<string[]>([])
const startDate = ref('')
const endDate = ref('')

const tools: Tool[] = [
  { id: 'zoom-in', icon: 'ZoomIn', tooltip: 'Acercar' },
  { id: 'zoom-out', icon: 'ZoomOut', tooltip: 'Alejar' },
  { id: 'home', icon: 'Home', tooltip: 'Vista inicial' },
  { id: 'filter', icon: 'Filter', tooltip: 'Filtros' }
]

const iconComponents = {
  ZoomIn: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>`,
  ZoomOut: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><line x1="8" y1="11" x2="14" y2="11"/></svg>`,
  Home: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9,22 9,12 15,12 15,22"/></svg>`,
  Filter: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46 22,3"/></svg>`
}

const handleToolClick = (toolId: string) => {
  if (toolId === 'zoom-in') {
    triggerZoomIn()
  } else if (toolId === 'zoom-out') {
    triggerZoomOut()
  } else if (toolId === 'home') {
    triggerResetView()
  } else {
    activeTool.value = activeTool.value === toolId ? '' : toolId
  }
}

const applyFiltersHandler = () => {
  applyFilters(selectedConcepts.value, startDate.value, endDate.value)
  // Opcional: cerrar panel
  // activeTool.value = ''
}

const clearFiltersHandler = () => {
  selectedConcepts.value = []
  startDate.value = ''
  endDate.value = ''
  clearFilters()
}

const handleETLModalClose = () => {
  showETLModal.value = false
}

// Lógica de Notificaciones
const checkUpdates = async () => {
  try {
    const response = await fetch('/api/etl/notifications/check-updates/', { method: 'POST' })
    const data = await response.json()
    if (data.status === 'success') {
      unreadCount.value = data.unread_count
      if (data.new_notifications > 0) {
        // Opcional: Mostrar toast o alerta
        console.log(`Se encontraron ${data.new_notifications} nuevas actualizaciones`)
      }
    }
  } catch (error) {
    console.error('Error checking updates:', error)
  }
}

const fetchNotifications = async () => {
  loadingNotifications.value = true
  try {
    const response = await fetch('/api/etl/notifications/list_unread/')
    const data = await response.json()
    notifications.value = data
  } catch (error) {
    console.error('Error fetching notifications:', error)
  } finally {
    loadingNotifications.value = false
  }
}

const toggleNotifications = () => {
  showNotifications.value = !showNotifications.value
  if (showNotifications.value) {
    fetchNotifications()
  }
}

const markAsRead = async (notif: any) => {
  try {
    await fetch(`/api/etl/notifications/${notif.id}/mark_read/`, { method: 'POST' })
    notif.is_read = true
    // Remover de la lista o actualizar contador
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    notifications.value = notifications.value.filter(n => n.id !== notif.id)
  } catch (error) {
    console.error('Error marking as read:', error)
  }
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

onMounted(() => {
  checkUpdates()
})
</script>

<style scoped>
.sidebar {
  width: 55px;
  background: #262626;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px 0;
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.15);
  z-index: 999;
  height: 100%;
  justify-content: space-between;
  position: relative; /* Para posicionar el panel */
}

.filter-panel, .notification-panel {
  position: absolute;
  left: 60px;
  top: 15px;
  width: 250px;
  background: #333;
  color: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  z-index: 1000;
}

.notification-panel {
  width: 320px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  top: 60px; /* Ajustar posición */
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  border-bottom: 1px solid #555;
  padding-bottom: 10px;
}

.notification-header h3 {
  margin: 0;
  font-size: 16px;
}

.close-btn {
  background: none;
  border: none;
  color: #aaa;
  cursor: pointer;
  font-size: 18px;
}

.notification-list {
  overflow-y: auto;
  flex: 1;
}

.notification-item {
  background: #444;
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: background 0.2s;
}

.notification-item:hover {
  background: #555;
}

.notif-title {
  font-weight: bold;
  font-size: 13px;
  margin-bottom: 4px;
  color: #fff;
}

.notif-codes {
  font-size: 11px;
  color: #aaa;
  display: flex;
  gap: 10px;
  margin-bottom: 6px;
}

.notif-change {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 4px;
}

.concept {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
}

.concept.old {
  background: #555;
  color: #ccc;
}

.concept.new {
  background: #3498db;
  color: white;
}

.arrow {
  color: #aaa;
}

.notif-date {
  font-size: 10px;
  color: #888;
  text-align: right;
}

.notification-btn {
  position: relative;
}

.notification-badge {
  position: absolute;
  top: 0;
  right: 0;
  background: #e74c3c;
  color: white;
  font-size: 10px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.filter-panel h3 {
  margin-top: 0;
  margin-bottom: 15px;
  border-bottom: 1px solid #555;
  padding-bottom: 5px;
}

.filter-section {
  margin-bottom: 15px;
}

.filter-section h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #aaa;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
}

.date-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.date-group input {
  background: #444;
  border: 1px solid #555;
  color: white;
  padding: 5px;
  border-radius: 4px;
}

.filter-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-apply, .btn-clear {
  flex: 1;
  padding: 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-apply {
  background: #3498db;
  color: white;
}

.btn-apply:hover {
  background: #2980b9;
}

.btn-clear {
  background: #e74c3c;
  color: white;
}

.btn-clear:hover {
  background: #c0392b;
}

.tool-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-button {
  width: 42px;
  height: 42px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #ecf0f1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  position: relative;
}

.tool-button:hover {
  background: #34495e;
  transform: translateX(2px);
}

.tool-button.active {
  background: #3498db;
  color: white;
  box-shadow: 0 0 10px rgba(52, 152, 219, 0.5);
}

.tool-button:hover::after {
  content: attr(title);
  position: absolute;
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  background: #34495e;
  color: white;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  margin-left: 10px;
  z-index: 1000;
}

.tool-button span {
  display: flex;
  align-items: center;
  justify-content: center;
}

.tool-button svg {
  color: inherit;
}

.navbar-icons {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 10px;
}

.navbar-icon-btn {
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

.navbar-icon-btn:hover {
  background: #34495e;
}

.navbar-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
}
</style>
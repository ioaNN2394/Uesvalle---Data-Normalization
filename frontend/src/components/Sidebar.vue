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
        <div class="header-title">
          <svg class="bell-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
          </svg>
          <h3>Notificaciones{{ unreadCount > 0 ? ` (${unreadCount})` : '' }}</h3>
        </div>
        <button @click="showNotifications = false" class="close-btn" aria-label="Cerrar notificaciones">✕</button>
      </div>
      <div v-if="notifications.length > 0" class="notification-actions">
        <button @click="openConfirmDeleteAll" class="btn-delete-all">Eliminar todas las notificaciones</button>
      </div>
      <div v-if="loadingNotifications" class="loading-state">
        <div class="skeleton" v-for="i in 3" :key="i">
          <div class="skeleton-line skeleton-title"></div>
          <div class="skeleton-line skeleton-change"></div>
          <div class="skeleton-line skeleton-date"></div>
        </div>
      </div>
      <div v-else-if="errorNotifications" class="error-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        <p>Error al cargar notificaciones</p>
        <button @click="fetchNotifications" class="btn-retry">Reintentar</button>
      </div>
      <div v-else-if="notifications.length === 0" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
        </svg>
        <p>No hay notificaciones nuevas</p>
      </div>
      <div v-else class="notification-list">
        <div 
          v-for="notif in notifications" 
          :key="notif.id" 
          class="notification-item"
          :class="{ unread: !notif.is_read }"
        >
          <div class="unread-indicator" v-if="!notif.is_read"></div>
          <button @click.stop="deleteNotification(notif.id)" class="delete-notif-btn" title="Eliminar notificación" aria-label="Eliminar notificación">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M10 11v6M14 11v6"/>
            </svg>
          </button>
          <div @click="markAsRead(notif)" @keydown.enter="markAsRead(notif)" @keydown.space.prevent="markAsRead(notif)" class="notif-content" tabindex="0" role="button" :aria-label="`Notificación de ${notif.institucion_nombre}: ${notif.old_concept || 'N/A'} → ${notif.new_concept}`">
            <div class="notif-title">{{ notif.institucion_nombre }}</div>
            <div class="notif-codes">DANE: {{ notif.institucion_dane }} | UES: {{ notif.institucion_ues }}</div>
            <div class="notif-change">
              <span class="concept-badge old" :title="getConceptTooltip(notif.old_concept || 'N/A')">{{ notif.old_concept || 'N/A' }}</span>
              <svg class="arrow-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
              <span class="concept-badge new" :title="getConceptTooltip(notif.new_concept)">{{ notif.new_concept }}</span>
            </div>
            <div class="notif-date" :title="formatFullDate(notif.created_at)">{{ formatRelativeDate(notif.created_at) }}</div>
          </div>
        </div>
      </div>
    </div>

    <ETLUploadModal 
      :is-open="showETLModal" 
      @close="handleETLModalClose"
    />
    <!-- Confirm Delete All Modal -->
    <div v-if="showConfirmDeleteAll" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="confirm-delete-title" @click="closeConfirmDeleteAll">
      <div class="modal-dialog" @click.stop>
        <h3 id="confirm-delete-title">Eliminar todas las notificaciones</h3>
        <p>¿Está seguro de que desea eliminar todas las notificaciones? Esta acción no se puede deshacer.</p>
        <div class="modal-actions">
          <button class="modal-btn modal-cancel" @click="closeConfirmDeleteAll">Cancelar</button>
          <button class="modal-btn modal-confirm" @click="performDeleteAll" ref="confirmDeleteAllBtnRef">Eliminar</button>
        </div>
      </div>
    </div>
    <ReportModal v-if="showReportModal" @close="showReportModal = false" />
  </aside>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
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
const errorNotifications = ref(false)
// Modal confirmation state
const showConfirmDeleteAll = ref(false)
const confirmDeleteAllBtnRef = ref<HTMLButtonElement | null>(null)
let escListener: ((e: KeyboardEvent) => void) | null = null

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
  errorNotifications.value = false
  try {
    const response = await fetch('/api/etl/notifications/list_unread/')
    const data = await response.json()
    notifications.value = data
  } catch (error) {
    console.error('Error fetching notifications:', error)
    errorNotifications.value = true
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

const deleteNotification = async (notifId: string) => {
  try {
    await fetch(`/api/etl/notifications/${notifId}/delete_notification/`, { method: 'DELETE' })
    // Remover de la lista y actualizar contador
    notifications.value = notifications.value.filter(n => n.id !== notifId)
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  } catch (error) {
    console.error('Error deleting notification:', error)
  }
}

const openConfirmDeleteAll = async () => {
  showConfirmDeleteAll.value = true
  await nextTick()
  // focus on confirm button
  if (confirmDeleteAllBtnRef.value) confirmDeleteAllBtnRef.value.focus()
  // add escape key listener
  escListener = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      closeConfirmDeleteAll()
    }
  }
  window.addEventListener('keydown', escListener)
}

const closeConfirmDeleteAll = () => {
  showConfirmDeleteAll.value = false
  if (escListener) {
    window.removeEventListener('keydown', escListener)
    escListener = null
  }
}

const performDeleteAll = async () => {
  try {
    await fetch('/api/etl/notifications/delete-all/', { method: 'DELETE' })
    // Limpiar la lista y el contador
    notifications.value = []
    unreadCount.value = 0
    showConfirmDeleteAll.value = false
  } catch (error) {
    console.error('Error deleting all notifications:', error)
  } finally {
    if (escListener) {
      window.removeEventListener('keydown', escListener)
      escListener = null
    }
  }
}

const formatRelativeDate = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return 'ahora'
  if (diffMins < 60) return `hace ${diffMins} min`
  if (diffHours < 24) return `hace ${diffHours} h`
  if (diffDays < 7) return `hace ${diffDays} d`
  return date.toLocaleDateString()
}

const formatFullDate = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

const getConceptTooltip = (concept: string) => {
  const tooltips: { [key: string]: string } = {
    'F': 'Favorable',
    'D': 'Desfavorable',
    'FCR': 'Favorable con Recomendaciones'
  }
  return tooltips[concept] || concept
}

onMounted(() => {
  checkUpdates()
})

onBeforeUnmount(() => {
  if (escListener) {
    window.removeEventListener('keydown', escListener)
  }
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
  top: 60px;
  max-width: 90vw;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  border-bottom: 1px solid #555;
  padding-bottom: 10px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bell-icon {
  color: #3498db;
}

.notification-header h3 {
  margin: 0;
  font-size: 16px;
  color: #fff;
}

.close-btn {
  background: none;
  border: none;
  color: #aaa;
  cursor: pointer;
  font-size: 18px;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: #555;
  color: #fff;
}

.notification-list {
  overflow-y: auto;
  flex: 1;
  max-height: 400px;
}

.notification-item {
  background: #444;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
  position: relative;
  border-left: 4px solid transparent;
}

.notification-item.unread {
  background: rgba(52, 152, 219, 0.05);
  border-left-color: #3498db;
}

.notification-item:hover {
  background: #4a4a4a;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.unread-indicator {
  position: absolute;
  left: -2px;
  top: 16px;
  width: 8px;
  height: 8px;
  background: #3498db;
  border-radius: 50%;
  border: 2px solid #333;
}

.notif-title {
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 8px;
  color: #fff;
  line-height: 1.3;
}

.notif-codes {
  font-size: 12px;
  color: #aaa;
  margin-bottom: 12px;
  font-family: 'Courier New', monospace;
  opacity: 0.8;
}

.notif-change {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.concept-badge {
  padding: 4px 8px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.concept-badge.old {
  background: #555;
  color: #ccc;
  border: 1px solid #666;
}

.concept-badge.new {
  background: linear-gradient(135deg, #f39c12, #e67e22);
  color: white;
  border: 1px solid #d35400;
  box-shadow: 0 1px 3px rgba(243, 156, 18, 0.3);
}

.arrow-icon {
  color: #888;
  flex-shrink: 0;
}

.notif-date {
  font-size: 11px;
  color: #888;
  text-align: right;
  opacity: 0.7;
}

.notification-actions {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #555;
}

.btn-delete-all {
  width: 100%;
  padding: 10px;
  background: #7f8c8d;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-delete-all:hover {
  background: #95a5a6;
  transform: translateY(-1px);
}

.delete-notif-btn {
  position: absolute;
  bottom: 12px;
  left: 12px;
  background-color: #ef4444;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: all 150ms ease-out;
  color: white;
  opacity: 0;
  z-index: 10;
}

.notification-item:hover .delete-notif-btn {
  opacity: 1;
}

.delete-notif-btn:hover {
  background-color: #dc2626;
  transform: scale(1.1);
}

.delete-notif-btn:active {
  transform: scale(0.95);
}

.delete-notif-btn:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  opacity: 1;
}

.notif-content {
  cursor: pointer;
}

.loading-state {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
}

.skeleton {
  background: #444;
  border-radius: 8px;
  padding: 16px;
}

.skeleton-line {
  background: #555;
  border-radius: 4px;
  height: 12px;
  margin-bottom: 8px;
  animation: pulse 1.5s ease-in-out infinite;
}

.skeleton-title {
  width: 70%;
  height: 16px;
}

.skeleton-change {
  width: 50%;
  height: 14px;
}

.skeleton-date {
  width: 30%;
  height: 10px;
  margin-bottom: 0;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.empty-state, .error-state {
  text-align: center;
  padding: 40px 20px;
  color: #aaa;
}

.empty-state svg, .error-state svg {
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p, .error-state p {
  margin: 0 0 16px 0;
  font-size: 14px;
}

.btn-retry {
  padding: 8px 16px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s;
}

.btn-retry:hover {
  background: #2980b9;
}

/* Modal: confirm delete all */
.modal-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.35);
  backdrop-filter: blur(5px);
  z-index: 3000;
}

.modal-dialog {
  width: 90%;
  max-width: 420px;
  background: #222;
  color: #fff;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 24px 48px rgba(0,0,0,0.6);
  transform: translateY(-8px);
  opacity: 0;
  animation: modalShow 200ms ease-out forwards;
}

@keyframes modalShow {
  to { transform: translateY(0); opacity: 1; }
}

.modal-dialog h3 {
  margin: 0 0 12px 0;
  font-size: 18px;
}

.modal-dialog p { margin: 0 0 16px 0; color: #ddd; }

.modal-actions { display: flex; gap: 10px; justify-content: flex-end; }

.modal-btn { padding: 8px 12px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; }
.modal-cancel { background: transparent; color: #ddd; border: 1px solid rgba(255,255,255,0.06); }
.modal-confirm { background: #ef4444; color: white; }

.modal-confirm:hover { background: #dc2626; transform: translateY(-1px); }
.modal-cancel:hover { background: rgba(255,255,255,0.03); }

/* Accessibility */
.notif-content:focus {
  outline: 2px solid #3498db;
  outline-offset: 2px;
}

.delete-notif-btn:focus {
  outline: 2px solid #e74c3c;
  outline-offset: 2px;
}

.btn-delete-all:focus,
.btn-retry:focus,
.close-btn:focus {
  outline: 2px solid #3498db;
  outline-offset: 2px;
}

/* Responsive */
@media (max-width: 768px) {
  .notification-panel {
    width: 90vw;
    max-width: 400px;
    left: 5vw;
  }
  
  .notification-item {
    padding: 12px;
  }
  
  .notif-title {
    font-size: 14px;
  }
  
  .delete-notif-btn {
    opacity: 1;
  }
}

@media (max-width: 480px) {
  .notification-panel {
    width: 95vw;
    left: 2.5vw;
    top: 70px;
  }
  
  .notification-header h3 {
    font-size: 14px;
  }
  
  .notif-codes {
    font-size: 11px;
  }
  
  .delete-notif-btn {
    opacity: 1;
  }
}

.notif-content {
  cursor: pointer;
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
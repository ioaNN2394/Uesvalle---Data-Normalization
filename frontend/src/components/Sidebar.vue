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
      <button class="navbar-icon-btn" title="Notificaciones">
        <img src="/campana.png" alt="Notificaciones" class="navbar-icon" />
      </button>
      <button class="navbar-icon-btn" title="Reportes" @click="showReportModal = true">
        <img src="/reporte.png" alt="Reportes" class="navbar-icon" />
      </button>
    </div>

    <ETLUploadModal 
      :is-open="showETLModal" 
      @close="handleETLModalClose"
    />
    <ReportModal v-if="showReportModal" @close="showReportModal = false" />
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ReportModal from '../modules/reports/components/ReportModal.vue'
import ETLUploadModal from '../modules/etl/components/ETLUploadModal.vue'

interface Tool {
  id: string
  icon: string
  tooltip: string
}

const activeTool = ref<string>('')
const showReportModal = ref(false)
const showETLModal = ref(false)
const etlButtonRef = ref<HTMLButtonElement | null>(null)

const tools: Tool[] = [
  { id: 'zoom-in', icon: 'ZoomIn', tooltip: 'Acercar' },
  { id: 'zoom-out', icon: 'ZoomOut', tooltip: 'Alejar' },
  { id: 'home', icon: 'Home', tooltip: 'Vista inicial' },
  { id: 'layers', icon: 'Layers', tooltip: 'Capas y leyenda' },
  { id: 'measure', icon: 'Ruler', tooltip: 'Herramientas de medición' },
  { id: 'filter', icon: 'Filter', tooltip: 'Filtros' }
]

const iconComponents = {
  ZoomIn: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>`,
  ZoomOut: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><line x1="8" y1="11" x2="14" y2="11"/></svg>`,
  Home: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9,22 9,12 15,12 15,22"/></svg>`,
  Layers: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12,2 2,7 12,12 22,7 12,2"/><polyline points="2,17 12,22 22,17"/><polyline points="2,12 12,17 22,12"/></svg>`,
  Ruler: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.3 8.7l-9.6 9.6c-.9.9-2.4.9-3.3 0l-5.7-5.7c-.9-.9-.9-2.4 0-3.3l9.6-9.6c.9-.9 2.4-.9 3.3 0l5.7 5.7c.9.9.9 2.4 0 3.3z"/><path d="m14.5 9.5-5 5"/><path d="m12 7 2 2"/><path d="m10 11 2 2"/></svg>`,
  Filter: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46 22,3"/></svg>`
}

const handleToolClick = (toolId: string) => {
  activeTool.value = activeTool.value === toolId ? '' : toolId
  console.log('Tool clicked:', toolId)
}

const handleETLModalClose = () => {
  showETLModal.value = false
  // El foco se devuelve automáticamente desde el modal
}
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
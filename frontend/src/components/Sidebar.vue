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
        <component :is="tool.icon" :size="20" />
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { 
  Plus, 
  Minus, 
  Home, 
  Layers, 
  Ruler, 
  Filter, 
  Bell 
} from 'lucide-vue-next'

interface Tool {
  id: string
  icon: any
  tooltip: string
}

const activeTool = ref<string>('')

const tools: Tool[] = [
  { id: 'zoom-in', icon: Plus, tooltip: 'Acercar' },
  { id: 'zoom-out', icon: Minus, tooltip: 'Alejar' },
  { id: 'home', icon: Home, tooltip: 'Vista inicial' },
  { id: 'layers', icon: Layers, tooltip: 'Capas y leyenda' },
  { id: 'measure', icon: Ruler, tooltip: 'Herramientas de medición' },
  { id: 'filter', icon: Filter, tooltip: 'Filtros' },
  { id: 'notifications', icon: Bell, tooltip: 'Notificaciones' }
]

const handleToolClick = (toolId: string): void => {
  activeTool.value = activeTool.value === toolId ? '' : toolId
  console.log('Tool clicked:', toolId)
  // TODO: Implementar lógica específica para cada herramienta
}
</script>

<style scoped>
.sidebar {
  width: 50px;
  background: #2c3e50;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
  box-shadow: 2px 0 4px rgba(0, 0, 0, 0.1);
  z-index: 999;
}

.tool-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-button {
  width: 40px;
  height: 40px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #ecf0f1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.tool-button:hover {
  background: #34495e;
  transform: translateY(-1px);
}

.tool-button.active {
  background: #3498db;
  color: white;
}
</style>
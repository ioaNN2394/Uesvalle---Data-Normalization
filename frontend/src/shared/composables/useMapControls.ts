import { ref, reactive } from 'vue'

// Global state for map controls
const zoomAction = ref<'in' | 'out' | 'reset' | null>(null)
const selectedInstitutionAction = ref<{ id: string, lat: number, lon: number } | null>(null)
const filterState = reactive({
  conceptos: [] as string[], // ['F', 'D', 'FCR']
  fechaInicio: '',
  fechaFin: '',
  active: false
})

export function useMapControls() {
  
  function triggerZoomIn() {
    zoomAction.value = 'in'
    // Reset after a tick to allow re-triggering
    setTimeout(() => zoomAction.value = null, 100)
  }

  function triggerZoomOut() {
    zoomAction.value = 'out'
    setTimeout(() => zoomAction.value = null, 100)
  }

  function triggerResetView() {
    zoomAction.value = 'reset'
    setTimeout(() => zoomAction.value = null, 100)
  }

  function selectInstitution(id: string, lat: number, lon: number) {
    console.log('useMapControls: selectInstitution called', { id, lat, lon })
    selectedInstitutionAction.value = { id, lat, lon }
    // Reset after a tick to allow re-triggering if needed, though for selection it might persist
    setTimeout(() => {
      selectedInstitutionAction.value = null
    }, 500)
  }

  function applyFilters(conceptos: string[], inicio: string, fin: string) {
    filterState.conceptos = conceptos
    filterState.fechaInicio = inicio
    filterState.fechaFin = fin
    filterState.active = true
  }

  function clearFilters() {
    filterState.conceptos = []
    filterState.fechaInicio = ''
    filterState.fechaFin = ''
    filterState.active = false
  }

  return {
    zoomAction,
    selectedInstitutionAction,
    filterState,
    triggerZoomIn,
    triggerZoomOut,
    triggerResetView,
    selectInstitution,
    applyFilters,
    clearFilters
  }
}

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
        <span v-if="tool.id === 'filter' && activeFiltersCount > 0" class="tool-badge">{{ activeFiltersCount }}</span>
      </button>
    </div>
    
    <!-- Panel de Filtros -->
    <div v-if="activeTool === 'filter'" class="filter-panel" :class="{ 'has-error': dateError, 'filters-active': hasFilters }">
      <div class="filter-header">
        <div class="filter-title">
          <svg class="filter-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46 22,3"/>
          </svg>
          <h3>Filtros <span class="badge" v-if="activeFiltersCount > 0">{{ activeFiltersCount }}</span></h3>
        </div>
        <button 
          class="btn-view-institutions" 
          :disabled="!filtersApplied" 
          @click="openInstitutionsModal"
          title="Ver instituciones que coinciden con los filtros"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          Ver instituciones
        </button>
      </div>
      
      <div class="filter-section card">
        <div class="section-header" @click="toggleSection('concepts')" @keydown.enter="toggleSection('concepts')" @keydown.space.prevent="toggleSection('concepts')" role="button" tabindex="0" :aria-expanded="sectionOpen.concepts">
          <h4>Concepto Visita</h4>
          <svg class="chevron" :class="{'rotated': sectionOpen.concepts}" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
        <transition name="collapse">
          <div v-show="sectionOpen.concepts" class="section-content">
          <div class="checkbox-card">
            <label class="checkbox-label" tabindex="0">
              <input type="checkbox" value="F" v-model="selectedConcepts" />
              <span class="custom-checkbox" aria-hidden="true"></span>
              <span class="label-text">Favorable (F)</span>
            </label>
            <label class="checkbox-label" tabindex="0">
              <input type="checkbox" value="D" v-model="selectedConcepts" />
              <span class="custom-checkbox" aria-hidden="true"></span>
              <span class="label-text">Desfavorable (D)</span>
            </label>
            <label class="checkbox-label" tabindex="0">
              <input type="checkbox" value="FCR" v-model="selectedConcepts" />
              <span class="custom-checkbox" aria-hidden="true"></span>
              <span class="label-text">Favorable con Rec. (FCR)</span>
            </label>
          </div>
          </div>
        </transition>
      </div>
      
      <div class="filter-section card">
        <div class="section-header" @click="toggleSection('dates')" @keydown.enter="toggleSection('dates')" @keydown.space.prevent="toggleSection('dates')" role="button" tabindex="0" :aria-expanded="sectionOpen.dates">
          <h4>Fecha de Visita</h4>
          <svg class="chevron" :class="{'rotated': sectionOpen.dates}" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
        <transition name="collapse">
          <div v-show="sectionOpen.dates" class="section-content">
          <div class="date-grid">
            <div class="date-item">
              <label class="date-label">Desde</label>
              <div class="date-input-wrapper">
                <input type="date" v-model="startDate" :max="maxDate" :aria-invalid="dateError">
                <svg class="calendar-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/></svg>
              </div>
            </div>
            <div class="date-item">
              <label class="date-label">Hasta</label>
              <div class="date-input-wrapper">
                <input type="date" v-model="endDate" :max="maxDate" :aria-invalid="dateError">
                <svg class="calendar-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/></svg>
              </div>
              <div class="date-error" v-if="startDate && endDate && startDate > endDate">
                La fecha 'Hasta' debe ser mayor a 'Desde'
              </div>
              <div class="date-error" v-if="startDate && startDate > maxDate">
                No puedes poner una fecha superior a hoy (Fecha 'Desde')
              </div>
              <div class="date-error" v-if="endDate && endDate > maxDate">
                No puedes poner una fecha superior a hoy (Fecha 'Hasta')
              </div>
            </div>
          </div>
          </div>
        </transition>
      </div>
      
      <div class="filter-actions">
        <button @click="applyFiltersHandler" class="btn-apply" :disabled="applyDisabled || dateError">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>
          Aplicar
        </button>
        <button @click="clearFiltersHandler" class="btn-clear" :disabled="!hasFilters">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/></svg>
          Borrar
        </button>
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

    <!-- Modal de Instituciones Filtradas -->
    <Teleport to="body">
      <div v-if="showInstitutionsModal" class="institutions-modal-overlay" @click.self="closeInstitutionsModal">
        <div class="institutions-modal">
          <div class="institutions-modal-header">
            <h2>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
              Instituciones Filtradas
              <span class="institutions-count" v-if="filteredInstitutions.length > 0">({{ filteredInstitutions.length }})</span>
            </h2>
            <button class="modal-close-btn" @click="closeInstitutionsModal" aria-label="Cerrar">✕</button>
          </div>
          
          <!-- Barra de búsqueda -->
          <div class="institutions-search-container">
            <div class="institutions-search">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input 
                type="text" 
                v-model="institutionSearch" 
                @input="debouncedSearch"
                placeholder="Buscar por nombre, DANE o UES"
                class="institutions-search-input"
                :disabled="loadingInstitutions"
              />
              <button v-if="institutionSearch" class="search-clear-btn" @click="institutionSearch = ''" aria-label="Limpiar búsqueda">✕</button>
            </div>
            <div v-if="searchedInstitutions.length > 0" class="search-results-info">
              Mostrando {{ searchedInstitutions.length }} de {{ filteredInstitutions.length }}
            </div>
          </div>
          
          <!-- Loading state -->
          <div v-if="loadingInstitutions" class="institutions-loading">
            <div class="spinner"></div>
            <p>Cargando instituciones...</p>
          </div>
          
          <!-- Empty state -->
          <div v-else-if="searchedInstitutions.length === 0" class="institutions-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
              <circle cx="12" cy="12" r="10"/>
              <path d="M8 15h8M9 9h.01M15 9h.01"/>
            </svg>
            <p v-if="institutionSearch">No se encontraron instituciones con "{{ institutionSearch }}"</p>
            <p v-else>No hay instituciones que coincidan con los filtros aplicados</p>
          </div>
          
          <!-- Lista de instituciones -->
          <div v-else class="institutions-list">
            <div 
              v-for="inst in searchedInstitutions" 
              :key="inst.institucion_id || inst.id" 
              class="institution-item"
              :class="{ expanded: expandedInstitution === (inst.institucion_id || inst.id) }"
            >
              <div class="institution-header" @click="toggleInstitutionDetails(inst)">
                <div class="institution-info">
                  <h4 class="institution-name">{{ inst.institucion || inst.nombre || inst.nombreinstitucion || 'Institución sin nombre' }}</h4>
                  <div class="institution-codes">
                    <span v-if="inst.dane_ie_id" class="code-badge dane">DANE: {{ inst.dane_ie_id }}</span>
                    <span v-else class="code-badge dane empty">DANE: N/A</span>
                    <span class="code-separator">|</span>
                    <span v-if="inst.uesvalle_ie_id" class="code-badge ues">UES: {{ inst.uesvalle_ie_id }}</span>
                    <span v-else class="code-badge ues empty">UES: N/A</span>
                  </div>
                </div>
                <div class="institution-meta">
                  <span class="concepto-pill" :class="getConceptoClassMini(inst.concepto_actual)">
                    {{ getConceptoLabelMini(inst.concepto_actual) }}
                  </span>
                  <svg class="chevron-icon" :class="{ rotated: expandedInstitution === (inst.institucion_id || inst.id) }" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                </div>
              </div>
              
              <!-- Detalles expandibles (acordeón) -->
              <transition name="accordion">
                <div v-if="expandedInstitution === (inst.institucion_id || inst.id)" class="institution-details">
                  <div v-if="loadingInstitutionDetails" class="details-loading">
                    <div class="spinner-small"></div>
                    <span>Cargando detalles...</span>
                  </div>
                  <div v-else-if="institutionDetails">
                    <!-- Concepto Badge -->
                    <div class="detail-concepto" :class="getConceptoClassMini(institutionDetails.concepto_actual)">
                      {{ getConceptoLabelFull(institutionDetails.concepto_actual) }}
                    </div>
                    
                    <!-- Identificadores -->
                    <div class="detail-section">
                      <h5>Identificadores</h5>
                      <p><strong>ID UESValle:</strong> {{ institutionDetails.uesvalle_ie_id || 'No registrado' }}</p>
                      <p><strong>Código DANE:</strong> {{ institutionDetails.dane_ie_id || 'No registrado' }}</p>
                    </div>
                    
                    <!-- Información General -->
                    <div class="detail-section">
                      <h5>Información General</h5>
                      <p><strong>Municipio:</strong> {{ getInstMunicipio(institutionDetails) }}</p>
                      <p><strong>Dirección:</strong> {{ getInstDireccion(institutionDetails) }}</p>
                      <p><strong>Teléfono:</strong> {{ getInstTelefono(institutionDetails) }}</p>
                      <p v-if="institutionDetails.lat"><strong>Coordenadas:</strong> {{ institutionDetails.lat.toFixed(6) }}, {{ institutionDetails.lon.toFixed(6) }}</p>
                    </div>
                    
                    <!-- Historial de Visitas -->
                    <div class="detail-section" v-if="institutionDetails.visitas && institutionDetails.visitas.length > 0">
                      <h5>Historial de Visitas ({{ institutionDetails.total_visitas }})</h5>
                      <div class="visitas-mini-list">
                        <div 
                          v-for="(visita, idx) in institutionDetails.visitas.slice(0, 3)" 
                          :key="visita.id" 
                          class="visita-mini-item"
                          :class="{ 'visita-actual': idx === 0 }"
                        >
                          <div class="visita-mini-header">
                            <span class="visita-fecha">{{ formatDateShort(visita.fechavisita) }}</span>
                            <span class="visita-concepto-mini" :class="getConceptoClassMini(visita.conceptovisita)">
                              {{ visita.conceptovisita }}
                            </span>
                          </div>
                          <p class="visita-funcionario-mini">
                            {{ visita.nombrefuncionario }} {{ visita.apellidofuncionario }}
                          </p>
                        </div>
                        <p v-if="institutionDetails.visitas.length > 3" class="more-visitas">
                          +{{ institutionDetails.visitas.length - 3 }} visitas más
                        </p>
                      </div>
                    </div>
                    
                    <!-- Botón para ver en mapa -->
                    <button 
                      v-if="institutionDetails.lat && institutionDetails.lon" 
                      class="btn-view-on-map"
                      @click="viewOnMap(institutionDetails)"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                        <circle cx="12" cy="10" r="3"/>
                      </svg>
                      Ver en mapa
                    </button>
                  </div>
                </div>
              </transition>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onBeforeUnmount, computed, reactive } from 'vue'
import ReportModal from '../modules/reports/components/ReportModal.vue'
import ETLUploadModal from '../modules/etl/components/ETLUploadModal.vue'
import { useMapControls } from '../shared/composables/useMapControls'

// Configuración de API
const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const { triggerZoomIn, triggerZoomOut, triggerResetView, applyFilters, clearFilters, selectInstitution } = useMapControls()

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

// Track if filters have been applied (button clicked)
const filtersApplied = ref(false)

// Modal de instituciones filtradas
const showInstitutionsModal = ref(false)
const filteredInstitutions = ref<any[]>([])
const loadingInstitutions = ref(false)
const institutionSearch = ref('')
const expandedInstitution = ref<string | null>(null)
const institutionDetails = ref<any>(null)
const loadingInstitutionDetails = ref(false)
let searchTimeout: any = null

const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    // La búsqueda se actualiza automáticamente a través del computed
  }, 300)
}

// Section state: collapsed/expanded
const sectionOpen = reactive({ concepts: true, dates: true })

const toggleSection = (section: 'concepts' | 'dates') => {
  sectionOpen[section] = !sectionOpen[section]
}

const maxDate = computed(() => {
  const d = new Date()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
})

const dateError = computed(() => {
  if (!startDate.value || !endDate.value) return false
  if (startDate.value > endDate.value) return true
  if (startDate.value > maxDate.value) return true
  if (endDate.value > maxDate.value) return true
  return false
})

const activeFiltersCount = computed(() => {
  let count = 0
  count += selectedConcepts.value.length
  if (startDate.value) count += 1
  if (endDate.value) count += 1
  return count
})

const hasFilters = computed(() => activeFiltersCount.value > 0)
const applyDisabled = computed(() => false) // Apply remains enabled by default

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
  if (dateError.value) return
  applyFilters(selectedConcepts.value, startDate.value, endDate.value)
  filtersApplied.value = hasFilters.value
  // Opcional: cerrar panel
  // activeTool.value = ''
}

const clearFiltersHandler = () => {
  selectedConcepts.value = []
  startDate.value = ''
  endDate.value = ''
  filtersApplied.value = false
  clearFilters()
}

const handleETLModalClose = () => {
  showETLModal.value = false
}

// Lógica de Notificaciones
const checkUpdates = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/etl/notifications/check-updates/`, { method: 'POST' })
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
    const response = await fetch(`${API_BASE}/api/etl/notifications/list_unread/`)
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
    await fetch(`${API_BASE}/api/etl/notifications/${notif.id}/mark_read/`, { method: 'POST' })
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
    await fetch(`${API_BASE}/api/etl/notifications/${notifId}/delete_notification/`, { method: 'DELETE' })
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
    await fetch(`${API_BASE}/api/etl/notifications/delete-all/`, { method: 'DELETE' })
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

// ===== FUNCIONES PARA MODAL DE INSTITUCIONES =====

// Computed: filtrar instituciones por búsqueda
const searchedInstitutions = computed(() => {
  if (!institutionSearch.value.trim()) return filteredInstitutions.value
  const query = institutionSearch.value.toLowerCase().trim()
  return filteredInstitutions.value.filter((inst: any) => {
    const name = (inst.institucion || inst.nombre || inst.nombreinstitucion || '').toLowerCase()
    const dane = (inst.dane_ie_id || '').toString()
    const ues = (inst.uesvalle_ie_id || '').toString()
    return name.includes(query) || dane.includes(query) || ues.includes(query)
  })
})

// Abrir modal de instituciones
const openInstitutionsModal = async () => {
  showInstitutionsModal.value = true
  loadingInstitutions.value = true
  expandedInstitution.value = null
  institutionDetails.value = null
  institutionSearch.value = ''
  
  try {
    // Construir query params con los filtros aplicados
    const params = new URLSearchParams()
    if (selectedConcepts.value.length > 0) {
      params.append('conceptos', selectedConcepts.value.join(','))
    }
    if (startDate.value) {
      params.append('fecha_inicio', startDate.value)
    }
    if (endDate.value) {
      params.append('fecha_fin', endDate.value)
    }
    
    const queryString = params.toString()
    const url = `${API_BASE}/api/etl/map/markers/${queryString ? '?' + queryString : ''}`
    
    const response = await fetch(url)
    const data = await response.json()
    
    if (data.status === 'success') {
      filteredInstitutions.value = data.data || []
    }
  } catch (error) {
    console.error('Error fetching filtered institutions:', error)
    filteredInstitutions.value = []
  } finally {
    loadingInstitutions.value = false
  }
}

// Cerrar modal de instituciones
const closeInstitutionsModal = () => {
  showInstitutionsModal.value = false
  expandedInstitution.value = null
  institutionDetails.value = null
}

// Toggle detalles de institución (acordeón)
const toggleInstitutionDetails = async (inst: any) => {
  if (expandedInstitution.value === inst.id || expandedInstitution.value === inst.institucion_id) {
    expandedInstitution.value = null
    institutionDetails.value = null
    return
  }
  
  const instId = inst.institucion_id || inst.id
  expandedInstitution.value = instId
  loadingInstitutionDetails.value = true
  institutionDetails.value = null
  
  try {
    const response = await fetch(`${API_BASE}/api/etl/map/institucion/${instId}/`)
    const data = await response.json()
    
    if (data.status === 'success') {
      institutionDetails.value = data.institucion
    }
  } catch (error) {
    console.error('Error fetching institution details:', error)
  } finally {
    loadingInstitutionDetails.value = false
  }
}

// Ver en mapa
const viewOnMap = (inst: any) => {
  if (inst.lat && inst.lon) {
    selectInstitution(inst.id, Number(inst.lat), Number(inst.lon))
    closeInstitutionsModal()
  }
}

// Helper functions para info de institución
function getInstLatestMetadata(inst: any): any {
  if (!inst || !inst.visitas || inst.visitas.length === 0) return null
  return inst.visitas[0]?.metadata || null
}

function getInstMunicipio(inst: any): string {
  const metadata = getInstLatestMetadata(inst)
  return metadata?.nombremunicipio || inst?.codigo_municipio || 'N/A'
}

function getInstDireccion(inst: any): string {
  const metadata = getInstLatestMetadata(inst)
  return metadata?.direccionestablecimiento || inst?.direccion || 'N/A'
}

function getInstTelefono(inst: any): string {
  const metadata = getInstLatestMetadata(inst)
  return metadata?.celular || inst?.telefono || 'N/A'
}

// Concepto helpers
function getConceptoClassMini(concepto: string | null): string {
  if (!concepto) return 'sin-clasificar'
  switch (concepto.toUpperCase()) {
    case 'F': return 'favorable'
    case 'D': return 'desfavorable'
    case 'FCR': return 'favorable-req'
    default: return 'sin-clasificar'
  }
}

function getConceptoLabelMini(concepto: string | null): string {
  if (!concepto) return 'Sin clasificar'
  switch (concepto.toUpperCase()) {
    case 'F': return 'Favorable'
    case 'D': return 'Desfavorable'
    case 'FCR': return 'Favorable con Rec.'
    case 'P': return 'Pendiente'
    default: return 'Sin clasificar'
  }
}

function getConceptoLabelFull(concepto: string | null): string {
  if (!concepto) return 'Sin concepto'
  switch (concepto.toUpperCase()) {
    case 'F': return 'Favorable'
    case 'D': return 'Desfavorable'
    case 'FCR': return 'Favorable con Requerimientos'
    default: return concepto
  }
}

function formatDateShort(dateString: string | null): string {
  if (!dateString) return 'N/A'
  const parts = dateString.split('T')[0].split('-')
  const date = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]))
  return date.toLocaleDateString('es-CO', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
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
.filter-panel {
  --primary: #0ea5a4; /* teal-ish */
  --primary-hover: #05948f;
  --text-secondary: #bdbdbd;
  --border-secondary: #bbbbbb33;
  --error: #ef4444;
}
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

/* filter panel styling */
.filter-panel, .notification-panel {
  position: absolute;
  left: 60px;
  top: 15px;
  width: 320px;
  background: #1f2933;
  color: #e6eef0;
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

/* Collapse transition */
.collapse-enter-active, .collapse-leave-active { transition: max-height 200ms ease, opacity 200ms ease; overflow: hidden; }
.collapse-enter-from, .collapse-leave-to { max-height: 0; opacity: 0; }
.collapse-enter-to, .collapse-leave-from { max-height: 400px; opacity: 1; }

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
  margin-bottom: 0;
  padding-bottom: 6px;
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.filter-title { display: flex; align-items: center; gap: 10px; }
.filter-icon { color: var(--primary); }
.filter-header h3 { font-size: 20px; font-weight: 700; margin: 0; }
.badge { background: var(--primary); color: white; padding: 2px 8px; border-radius: 999px; font-size: 12px; margin-left: 8px; }

.filter-section.card { background: rgba(14,165,164,0.02); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.03); }
.section-header { display:flex; align-items:center; justify-content:space-between; gap: 8px; cursor:pointer; user-select:none; padding: 2px 4px; }
.section-header h4 { font-size: 14px; font-weight: 600; color: #dbeafe; margin: 0; }
.section-content { padding-top: 10px; }
.chevron { transition: transform 200ms ease; color: var(--text-secondary); }
.chevron.rotated { transform: rotate(180deg); }

.checkbox-card { display:flex; flex-direction:column; gap: 12px; padding: 6px; }
.checkbox-label { display:flex; align-items:center; gap: 10px; cursor:pointer; user-select:none; padding: 6px; border-radius: 6px; transition: background 150ms, color 150ms; }
.checkbox-label .label-text { font-size: 14px; color: var(--text-secondary); }
.checkbox-label:hover { background: rgba(255,255,255,0.02); }
.checkbox-label input[type="checkbox"] { opacity: 0; width: 0; height: 0; position: absolute; }
.custom-checkbox { width: 20px; height: 20px; border: 2px solid var(--primary); border-radius: 4px; display:inline-block; box-sizing: border-box; transition: all 150ms; background: transparent; }
.custom-checkbox::after {
  content: '';
  display: block;
  width: 12px; height: 12px; margin: 1px; opacity: 0; transform: scale(0.9);
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>');
  background-size: 12px 12px; background-repeat: no-repeat; background-position: center;
  transition: opacity 120ms, transform 150ms;
}
.checkbox-label input[type="checkbox"]:checked + .custom-checkbox { background: var(--primary); border-color: var(--primary); }
.checkbox-label input[type="checkbox"]:checked + .custom-checkbox::after { opacity: 1; transform: scale(1); }
.checkbox-label input[type="checkbox"]:focus + .custom-checkbox { box-shadow: 0 0 0 3px rgba(14,165,164,0.12); }
.checkbox-label input[type="checkbox"]:checked + .custom-checkbox { animation: checkboxBounce 150ms ease forwards; }

@keyframes checkboxBounce {
  0% { transform: scale(1); }
  40% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.date-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.date-item { display:flex; flex-direction: column; gap: 6px; }
.date-label { font-size: 12px; color: var(--text-secondary); }
.date-input-wrapper { position: relative; }
.date-input-wrapper input[type="date"] { width: 100%; padding: 10px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06); background: #fff; color: #111; font-family: monospace; font-size: 14px; }
.date-input-wrapper .calendar-icon { position:absolute; right: 8px; top: 50%; transform: translateY(-50%); color: var(--text-secondary); pointer-events: none; }
.date-input-wrapper input[type="date"]:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(14,165,164,0.08); }
.date-error { color: var(--error); font-size: 11px; margin-top: 6px; }

.filter-actions { display:flex; gap: 12px; margin-top: 18px; }
.btn-apply { background: var(--primary); color: white; border-radius: 8px; padding: 12px 16px; display:flex; gap: 8px; align-items:center; justify-content:center; font-weight:600; }
.btn-apply:hover { background: var(--primary-hover); box-shadow: 0 8px 20px rgba(14,165,164,0.12); }
.btn-apply[disabled] { opacity: 0.6; cursor: not-allowed; }
.btn-clear { background: transparent; border: 1px solid rgba(255,255,255,0.06); color: #cbd5e1; border-radius: 8px; padding: 12px 16px; font-weight:600; }
.btn-clear.small { display:flex; gap:8px; align-items:center; padding: 8px 10px; font-weight:600; }
.btn-clear:hover { background: rgba(255,255,255,0.02); border-color: var(--primary); color: white; }

.filter-panel.has-error h3 { color: var(--error); }
.filter-panel.filters-active .filter-icon { filter: none; }
.filter-panel.filters-active .filter-title h3 { color: #fff; }
.filter-panel .filter-title .filter-icon { filter: grayscale(1) opacity(0.9); }
.filter-panel .filter-title .filter-icon.active-indicator::after {
  content: '';
}

/* small-screen responsive date grid */
@media (max-width: 480px) { .date-grid { grid-template-columns: 1fr; } }
@media (max-width: 480px) { .filter-actions { flex-direction: column; gap: 8px; } }

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

.tool-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: #ef4444; /* small red badge */
  color: white;
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(0,0,0,0.35);
  line-height: 1;
}

.tool-button.active .tool-badge {
  background: #fde68a; /* ensure contrast when active, optional */
  color: #111;
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

/* ═══════════════════════════════════════════════════════════════════════════
   MODAL VER INSTITUCIONES
   ═══════════════════════════════════════════════════════════════════════════ */

.institutions-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.institutions-modal {
  background: linear-gradient(145deg, #1e293b, #0f172a);
  border-radius: 16px;
  width: 100%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  animation: slideUp 0.3s ease;
  overflow: hidden;
}

@keyframes slideUp {
  from { 
    opacity: 0;
    transform: translateY(20px) scale(0.98);
  }
  to { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.institutions-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(14, 165, 164, 0.2);
  background: rgba(0, 0, 0, 0.2);
}

.institutions-modal-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #f1f5f9;
  display: flex;
  align-items: center;
  gap: 10px;
}

.institutions-modal-header h2 svg {
  color: #0ea5a4;
}

.institutions-count {
  background: rgba(14, 165, 164, 0.2);
  color: #0ea5a4;
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
}

.modal-close-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.modal-close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.institutions-search-container {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.institutions-search {
  position: relative;
  display: flex;
  align-items: center;
}

.institutions-search svg {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #0ea5a4;
  pointer-events: none;
}

.institutions-search input {
  width: 100%;
  padding: 12px 40px 12px 40px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(14, 165, 164, 0.3);
  border-radius: 8px;
  color: #f1f5f9;
  font-size: 14px;
  transition: all 0.2s ease;
}

.institutions-search input::placeholder {
  color: #64748b;
}

.institutions-search input:focus {
  outline: none;
  border-color: #0ea5a4;
  background: rgba(14, 165, 164, 0.05);
  box-shadow: 0 0 0 3px rgba(14, 165, 164, 0.1);
}

.search-clear-btn {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 16px;
  padding: 4px;
  transition: color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-clear-btn:hover {
  color: #f1f5f9;
}

.search-results-info {
  font-size: 12px;
  color: #64748b;
  padding: 0 4px;
}

.institutions-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.institutions-list::-webkit-scrollbar {
  width: 6px;
}

.institutions-list::-webkit-scrollbar-track {
  background: transparent;
}

.institutions-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.institutions-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

.institutions-empty {
  text-align: center;
  padding: 40px 20px;
  color: #64748b;
}

.institutions-empty svg {
  width: 48px;
  height: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.institutions-empty p {
  margin: 0;
  font-size: 14px;
}

.institutions-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #64748b;
  gap: 16px;
}

.institutions-loading .spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(14, 165, 164, 0.2);
  border-top-color: #0ea5a4;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.institution-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  margin-bottom: 10px;
  overflow: hidden;
  transition: all 0.2s ease;
}

.institution-item:hover {
  border-color: rgba(14, 165, 164, 0.3);
  background: rgba(255, 255, 255, 0.05);
}

.institution-item.expanded {
  border-color: rgba(14, 165, 164, 0.4);
  background: rgba(14, 165, 164, 0.05);
}

.institution-header {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  cursor: pointer;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.institution-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.institution-name {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.institution-codes {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  flex-wrap: wrap;
}

.code-badge {
  background: rgba(14, 165, 164, 0.1);
  border: 1px solid rgba(14, 165, 164, 0.2);
  color: #0ea5a4;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.code-badge.empty {
  background: rgba(107, 114, 128, 0.1);
  border-color: rgba(107, 114, 128, 0.2);
  color: #9ca3af;
}

.code-separator {
  color: #64748b;
  font-weight: 300;
}

.institution-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
}

.concepto-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.concepto-pill.favorable {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.concepto-pill.favorable-req {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.concepto-pill.desfavorable {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.concepto-pill.pendiente {
  background: rgba(107, 114, 128, 0.15);
  color: #9ca3af;
}

.concepto-pill.sin-clasificar {
  background: rgba(100, 116, 139, 0.15);
  color: #cbd5e1;
}

.chevron-icon {
  color: #64748b;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.institution-item.expanded .chevron-icon {
  transform: rotate(180deg);
  color: #0ea5a4;
}

.institution-details {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  animation: expandDetails 0.2s ease;
}

@keyframes expandDetails {
  from { 
    opacity: 0;
    transform: translateY(-10px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

.detail-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: #64748b;
  font-size: 13px;
  gap: 10px;
}

.detail-loading .spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(14, 165, 164, 0.3);
  border-top-color: #0ea5a4;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.detail-concepto {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 12px;
}

.detail-concepto.favorable {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.detail-concepto.favorable-req {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.detail-concepto.desfavorable {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.detail-concepto.pendiente {
  background: rgba(107, 114, 128, 0.15);
  color: #9ca3af;
}

.detail-concepto.sin-clasificar {
  background: rgba(100, 116, 139, 0.15);
  color: #cbd5e1;
}

.detail-section {
  margin-bottom: 12px;
}

.detail-section h5 {
  font-size: 12px;
  font-weight: 600;
  color: #0ea5a4;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 8px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(14, 165, 164, 0.2);
}

.detail-section p {
  margin: 6px 0;
  font-size: 13px;
  color: #e2e8f0;
  line-height: 1.4;
}

.detail-section p strong {
  color: #cbd5e1;
  font-weight: 600;
}

.visitas-mini-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.visita-mini-item {
  background: rgba(14, 165, 164, 0.05);
  border: 1px solid rgba(14, 165, 164, 0.15);
  border-radius: 6px;
  padding: 8px;
  font-size: 12px;
}

.visita-mini-item.visita-actual {
  border-color: rgba(14, 165, 164, 0.3);
  background: rgba(14, 165, 164, 0.1);
}

.visita-mini-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.visita-fecha {
  color: #64748b;
  font-size: 11px;
}

.visita-concepto-mini {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 11px;
}

.visita-funcionario-mini {
  color: #cbd5e1;
  margin: 0;
  font-size: 12px;
}

.more-visitas {
  text-align: center;
  color: #64748b;
  font-size: 11px;
  margin: 0;
  padding: 4px 0;
}

.detail-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.btn-view-on-map {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #0ea5a4, #0d9488);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-view-on-map:hover {
  background: linear-gradient(135deg, #14b8a6, #0ea5a4);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(14, 165, 164, 0.3);
}

.btn-view-on-map svg {
  width: 16px;
  height: 16px;
}

/* Responsive para el modal */
@media (max-width: 640px) {
  .institutions-modal {
    max-width: 100%;
    max-height: 90vh;
    border-radius: 12px;
  }
  
  .institutions-modal-header {
    padding: 14px 16px;
  }
  
  .institutions-modal-header h2 {
    font-size: 16px;
  }
  
  .institutions-search-container {
    padding: 12px 16px;
  }
  
  .institution-header {
    padding: 12px 14px;
  }
  
  .institution-details {
    padding: 0 14px 14px 32px;
  }
}
</style>
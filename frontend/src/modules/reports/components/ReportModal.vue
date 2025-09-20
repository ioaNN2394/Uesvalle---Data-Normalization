// src/modules/reports/components/ReportModal.vue
<template>
  <div class="modal-overlay" @click.self="close">
    <div class="report-modal">
      <h2 class="modal-title">Generación de Reporte</h2>
      <form class="modal-form" @submit.prevent>
        <div class="fields-grid">
          <div v-for="field in fields" :key="field.key" class="modal-field">
            <label class="modal-label">{{ field.label }}</label>
            
            <!-- Selector para Año y Calendario -->
            <div v-if="field.type === 'select'" class="modal-input-group">
              <select class="modal-select" v-model="form[field.key]">
                <option value="" selected>Dejar en blanco o seleccionar</option>
                <option v-for="option in field.options" :key="option" :value="option">
                  {{ option }}
                </option>
              </select>
            </div>

            <!-- Input de texto para los demás campos -->
            <div v-else class="modal-input-group">
              <input
                class="modal-input"
                :placeholder="'Dejar en blanco generara un reporte general'"
                v-model="form[field.key]"
                type="text"
              />
              <button type="button" class="modal-search-btn">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-icon">
            <img src="/xls.png" alt="Exportar a XLS" class="action-icon" />
          </button>
          <button type="button" class="btn-icon">
            <img src="/pdf.png" alt="Exportar a PDF" class="action-icon" />
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineEmits, reactive } from 'vue'

const emit = defineEmits(['close'])
const close = () => emit('close')

type FieldKey =
  | 'anio'
  | 'institucion'
  | 'pae'
  | 'municipio'
  | 'estado'
  | 'calendario'
  | 'nivel'
  | 'concepto'

interface Field {
  key: FieldKey
  label: string
  type?: 'text' | 'select'
  options?: (string | number)[]
}

// --- Opciones para los selectores ---
const currentYear = new Date().getFullYear();
const years = Array.from({ length: 20 }, (_, i) => currentYear - i);
const calendarOptions = ['A', 'B'];

const fields: Field[] = [
  { key: 'anio', label: 'Año', type: 'select', options: years },
  { key: 'institucion', label: 'Institución', type: 'text' },
  { key: 'pae', label: 'PAE', type: 'text' },
  { key: 'municipio', label: 'Municipio', type: 'text' },
  { key: 'estado', label: 'Estado', type: 'text' },
  { key: 'calendario', label: 'Calendario', type: 'select', options: calendarOptions },
  { key: 'nivel', label: 'Nivel', type: 'text' },
  { key: 'concepto', label: 'Concepto Sanitario', type: 'text' }
]

const form = reactive<Record<FieldKey, string>>({
  anio: '',
  institucion: '',
  pae: '',
  municipio: '',
  estado: '',
  calendario: '',
  nivel: '',
  concepto: ''
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.2);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.report-modal {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1);
  padding: 24px 32px;
  width: 100%;
  max-width: 720px;
  display: flex;
  flex-direction: column;
}

.modal-title {
  font-size: 24px;
  font-weight: 700;
  text-align: center;
  margin: 0 0 24px 0;
  color: #111827;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
  align-items: flex-start;
  width: 100%;
}

.fields-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px 20px;
  width: 100%;
}

.modal-field {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.modal-label {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
  color: #374151;
  text-align: left;
}

.modal-input-group {
  display: flex;
  align-items: center;
  width: 100%;
  background-color: #f3f4f6;
  border-radius: 8px;
  border: 1px solid transparent;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.modal-input-group:focus-within {
  border-color: #a5b4fc;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.modal-input {
  flex: 1;
  padding: 10px 12px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #111827;
  outline: none;
}

.modal-input::placeholder {
  color: #9ca3af;
  font-size: 13px;
}

/* --- Estilos para el SELECT --- */
.modal-select {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  
  width: 100%;
  padding: 10px 32px 10px 12px; /* Espacio para la flecha */
  border: none;
  background-color: transparent;
  font-size: 14px;
  color: #111827;
  outline: none;
  cursor: pointer;

  background-image: url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%236b7280%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E');
  background-repeat: no-repeat;
  background-position: right 12px top 50%;
  background-size: .65em auto;
}

/* Color del texto cuando no hay nada seleccionado */
.modal-select:invalid,
.modal-select option[value=""] {
  color: #9ca3af;
}

.modal-search-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-start;
}

.btn-icon {
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
}

</style>
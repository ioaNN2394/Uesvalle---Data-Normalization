<template>
  <div class="file-queue-item" :class="statusClass" :role="role">
    <!-- File Info -->
    <div class="file-info">
      <div class="file-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
          <polyline points="13 2 13 9 20 9"></polyline>
        </svg>
      </div>

      <div class="file-details">
        <p class="file-name">{{ file.file.name }}</p>
        <p class="file-size">{{ formatFileSize(file.file.size) }}</p>
      </div>
    </div>

    <!-- Status & Progress -->
    <div class="file-status-section">
      <div v-if="file.status === 'pending'" class="status-badge pending">
        En cola
      </div>
      <div v-else-if="file.status === 'uploading'" class="status-badge uploading">
        Subiendo
      </div>
      <div v-else-if="file.status === 'completed'" class="status-badge completed">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        Completado
      </div>
      <div v-else-if="file.status === 'error'" class="status-badge error">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        Error
      </div>

      <span v-if="file.status === 'uploading'" class="progress-percentage">
        {{ file.progress }}%
      </span>
    </div>

    <!-- Progress Bar -->
    <div v-if="file.status === 'uploading' || file.status === 'completed'" class="progress-container">
      <div
        class="progress-bar"
        role="progressbar"
        :aria-valuenow="Math.round(file.progress)"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="`Progreso del archivo ${file.file.name}: ${Math.round(file.progress)}%`"
      >
        <div class="progress-fill" :style="{ width: `${file.progress}%` }"></div>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="file.status === 'error' && file.error" class="error-message" role="alert">
      {{ file.error }}
    </div>

    <!-- Actions -->
    <div class="file-actions">
      <button
        v-if="file.status === 'error' && !disabled"
        class="action-btn retry-btn"
        @click="handleRetry"
        :title="`Reintentar ${file.file.name}`"
        aria-label="Reintentar carga del archivo"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path>
          <path d="M21 3v5h-5"></path>
          <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path>
          <path d="M3 21v-5h5"></path>
        </svg>
        Reintentar
      </button>

      <button
        class="action-btn remove-btn"
        @click="handleRemove"
        :disabled="disabled"
        :title="`Eliminar ${file.file.name}`"
        aria-label="Eliminar archivo de la cola"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
        Quitar
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface QueuedFile {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'completed' | 'error'
  progress: number
  error?: string
}

const props = defineProps<{
  file: QueuedFile
  index: number
  disabled?: boolean
  role?: string
}>()

const emit = defineEmits<{
  remove: [fileId: string]
  retry: [fileId: string]
}>()

const statusClass = computed(() => ({
  'status-pending': props.file.status === 'pending',
  'status-uploading': props.file.status === 'uploading',
  'status-completed': props.file.status === 'completed',
  'status-error': props.file.status === 'error'
}))

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const handleRemove = () => {
  emit('remove', props.file.id)
}

const handleRetry = () => {
  emit('retry', props.file.id)
}
</script>

<style scoped>
.file-queue-item {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.file-queue-item:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.file-queue-item.status-error {
  background: #fef2f2;
  border-color: #fecaca;
}

.file-queue-item.status-completed {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.file-queue-item.status-uploading {
  background: #eff6ff;
  border-color: #bfdbfe;
}

/* File Info Row */
.file-info {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.file-icon {
  flex-shrink: 0;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: rgba(156, 163, 175, 0.1);
  border-radius: 4px;
}

.file-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  margin: 0;
  word-break: break-word;
}

.file-size {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

/* Status Section */
.file-status-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-badge.pending {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
}

.status-badge.uploading {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.status-badge.completed {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
  display: inline-flex;
}

.status-badge.completed svg {
  width: 14px;
  height: 14px;
}

.status-badge.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
  display: inline-flex;
}

.status-badge.error svg {
  width: 14px;
  height: 14px;
}

.progress-percentage {
  font-size: 12px;
  font-weight: 600;
  color: #1e40af;
  margin-left: auto;
}

/* Progress Bar */
.progress-container {
  width: 100%;
}

.progress-bar {
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3498db, #2980b9);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* Error Message */
.error-message {
  font-size: 12px;
  color: #991b1b;
  background: #fef2f2;
  padding: 8px 10px;
  border-radius: 4px;
  border-left: 2px solid #dc2626;
  margin: -4px 0 0 0;
}

/* Actions */
.file-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #374151;
}

.action-btn:hover:not(:disabled) {
  background: white;
  border-color: #9ca3af;
  color: #111827;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.retry-btn {
  color: #2563eb;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.retry-btn:hover:not(:disabled) {
  background: #dbeafe;
  border-color: #93c5fd;
}

.remove-btn {
  color: #dc2626;
  border-color: #fecaca;
  background: #fef2f2;
}

.remove-btn:hover:not(:disabled) {
  background: #fee2e2;
  border-color: #fca5a5;
}

/* Responsive */
@media (max-width: 640px) {
  .file-queue-item {
    padding: 10px;
    gap: 8px;
  }

  .file-info {
    gap: 8px;
  }

  .file-name {
    font-size: 12px;
  }

  .file-size {
    font-size: 11px;
  }

  .file-actions {
    flex-wrap: wrap;
  }

  .action-btn {
    padding: 5px 8px;
    font-size: 11px;
  }
}
</style>

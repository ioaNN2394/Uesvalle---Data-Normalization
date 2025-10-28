<template>
  <Teleport to="body">
    <div class="confirmation-overlay" @click.self="handleCancel">
      <div
        class="confirmation-dialog"
        role="alertdialog"
        :aria-labelledby="titleId"
        :aria-describedby="messageId"
      >
        <div class="confirmation-header">
          <h3 :id="titleId" class="confirmation-title">
            {{ title }}
          </h3>
          <button
            class="confirmation-close-btn"
            @click="handleCancel"
            aria-label="Cerrar diálogo"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div :id="messageId" class="confirmation-message">
          {{ message }}
        </div>

        <div class="confirmation-actions">
          <button
            class="btn btn-secondary"
            @click="handleCancel"
            :aria-label="cancelLabel"
          >
            {{ cancelLabel }}
          </button>
          <button
            :class="['btn', isDestructive ? 'btn-danger' : 'btn-primary']"
            @click="handleConfirm"
            :aria-label="confirmLabel"
          >
            {{ confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  message: {
    type: String,
    required: true
  },
  confirmLabel: {
    type: String,
    default: 'Confirmar'
  },
  cancelLabel: {
    type: String,
    default: 'Cancelar'
  },
  isDestructive: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const titleId = 'confirmation-title'
const messageId = 'confirmation-message'
const focusedElement = ref<HTMLElement | null>(null)

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  emit('cancel')
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    handleCancel()
  }
  if (e.key === 'Enter') {
    handleConfirm()
  }
}

onMounted(() => {
  focusedElement.value = document.activeElement as HTMLElement
  document.addEventListener('keydown', handleKeyDown)

  // Trampa de foco
  const dialog = document.querySelector('.confirmation-dialog')
  const focusableElements = dialog?.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )

  if (focusableElements && focusableElements.length > 0) {
    const firstElement = focusableElements[0] as HTMLElement
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement.focus()
          e.preventDefault()
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement.focus()
          e.preventDefault()
        }
      }
    }

    document.addEventListener('keydown', handleTabKey)

    // Enfoque inicial en el botón primario
    const primaryButton = dialog?.querySelector('.btn-primary, .btn-danger') as HTMLElement
    if (primaryButton) {
      primaryButton.focus()
    }
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)

  // Devolver foco
  if (focusedElement.value) {
    focusedElement.value.focus()
  }
})
</script>

<style scoped>
.confirmation-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.4);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(3px);
}

.confirmation-dialog {
  background: white;
  border-radius: 12px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.2);
  padding: 32px;
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.confirmation-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.confirmation-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.confirmation-close-btn {
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.confirmation-close-btn:hover {
  background: #f3f4f6;
  color: #111827;
}

.confirmation-message {
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
  margin: 0;
}

.confirmation-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 8px;
}

.btn {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover {
  background: #2980b9;
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
}

.btn-primary:focus-visible {
  outline: 2px solid #2980b9;
  outline-offset: 2px;
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover {
  background: #dc2626;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.btn-danger:focus-visible {
  outline: 2px solid #dc2626;
  outline-offset: 2px;
}

.btn-secondary {
  background: white;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.btn-secondary:focus-visible {
  outline: 2px solid #3498db;
  outline-offset: 2px;
}

/* Responsive */
@media (max-width: 640px) {
  .confirmation-dialog {
    max-width: calc(100vw - 32px);
    padding: 24px;
    gap: 16px;
  }

  .confirmation-actions {
    flex-direction: column-reverse;
  }

  .btn {
    width: 100%;
  }
}
</style>

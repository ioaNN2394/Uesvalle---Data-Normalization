# 📋 Módulo de Carga de Excel y CSV para Actualización de ETL

## 📚 Documentación Completa de Implementación

Esta documentación describe el nuevo módulo `ETL Upload` implementado siguiendo estándares W3C de accesibilidad (WAI-ARIA), Material Design y guías de UX/UI de USWDS.

---

## 🎯 Resumen de la Solución

El módulo permite a los usuarios cargar archivos Excel (.xlsx, .xls) y CSV (.csv) para actualizar el ETL con:

- ✅ **Validación robusta** de archivos
- ✅ **Interfaz drag-and-drop** intuitiva
- ✅ **Progreso visual** por archivo y global
- ✅ **Accesibilidad completa** (WCAG 2.1 AA)
- ✅ **Manejo de errores** claro
- ✅ **Confirmación** antes de cancelar
- ✅ **Gestión de foco** y teclado

---

## 📁 Estructura de Carpetas

```
frontend/src/modules/etl/
├── components/
│   ├── ETLUploadModal.vue          # Modal principal (1)
│   ├── UploadDropzone.vue          # Zona de arrastre (2)
│   ├── FileQueueItem.vue           # Ítem en cola (3)
│   └── ConfirmationDialog.vue      # Diálogo de confirmación (4)
├── services/
│   └── etlUploadService.ts         # Lógica de validación y carga
├── types/
│   └── etl.types.ts                # (Opcional) Tipos TypeScript
└── composables/
    └── useETLUpload.ts             # (Opcional) Composable reutilizable
```

### Integración en Sidebar

```
frontend/src/components/Sidebar.vue  # Botón "Actualización ETL"
```

---

## 🔧 Componentes Creados

### 1. **ETLUploadModal.vue** - Modal Principal

**Responsabilidad:** Gestionar el flujo completo de carga y orquestar subcomponentes.

**Props:**
```typescript
{
  isOpen: Boolean    // Controla visibilidad del modal
}
```

**Emits:**
```typescript
{
  close: void        // Emitido al cerrar el modal
}
```

**Características:**
- Validación de archivos (extensión, MIME, tamaño)
- Cola de archivos con estados
- Progreso global y por archivo
- Bloqueo de interfaz durante procesamiento
- Diálogo de confirmación antes de cancelar
- Gestión de foco y trampa de foco (trap)
- Anuncios para lectores de pantalla

**Validaciones:**
```
✓ Extensión: .xlsx, .xls, .csv
✓ MIME: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
       application/vnd.ms-excel
       text/csv
✓ Tamaño máximo: 50MB (configurable)
✓ Duplicados: Detecta archivos con el mismo nombre
```

---

### 2. **UploadDropzone.vue** - Zona de Arrastre

**Responsabilidad:** Proporcionar interfaz de selección/arrastre de archivos.

**Props:**
```typescript
{
  disabled: Boolean              // Desactiva la zona
  maxFileSize: Number            // Límite de tamaño (por defecto 50MB)
}
```

**Emits:**
```typescript
{
  filesSelected: [File[]]         // Emitido cuando se seleccionan archivos
}
```

**Características:**
- Soporte para **Drag & Drop**
- Botón de selección con `<input type="file">`
- Validación inmediata
- Estados visuales (hover, dragover, error)
- Accesible por teclado (Enter/Espacio en botón)
- Mensajes de error contextuales

**Microcopy:**
```
Zona vacía: "Arrastra tus archivos aquí o haz clic para seleccionarlos"
Límite: "Hasta 50 MB por archivo. Solo .xlsx, .xls y .csv."
Error: "Formato no permitido: solo .xlsx, .xls y .csv"
```

---

### 3. **FileQueueItem.vue** - Ítem en Cola

**Responsabilidad:** Mostrar estado individual de cada archivo.

**Props:**
```typescript
{
  file: QueuedFile                // Objeto con datos del archivo
  index: Number                   // Posición en la cola
  disabled?: Boolean              // Desactiva botones
  role?: String                   // Para accesibilidad
}
```

**Emits:**
```typescript
{
  remove: [fileId]                // Quitar archivo de cola
  retry: [fileId]                 // Reintentar después de error
}
```

**Estados del archivo:**
| Estado | Ícono | Color | Acción |
|--------|-------|-------|--------|
| **Pending** | ⏳ | Amarillo | En cola, esperando procesamiento |
| **Uploading** | ⬆️ | Azul | Con barra de progreso % |
| **Completed** | ✅ | Verde | Éxito, 100% completado |
| **Error** | ❌ | Rojo | Muestra mensaje, botón "Reintentar" |

---

### 4. **ConfirmationDialog.vue** - Diálogo de Confirmación

**Responsabilidad:** Solicitar confirmación antes de cancelar la operación.

**Props:**
```typescript
{
  title: String                   // Título del diálogo
  message: String                 // Mensaje de confirmación
  confirmLabel: String            // Texto botón confirmar (default: "Confirmar")
  cancelLabel: String             // Texto botón cancelar (default: "Cancelar")
  isDestructive: Boolean          // Estilo destructivo (rojo) si true
}
```

**Emits:**
```typescript
{
  confirm: void                   // Usuario confirma la acción
  cancel: void                    // Usuario cancela la acción
}
```

**Características:**
- Diálogo modal centrado
- Trampa de foco (focus trap)
- Manejo de ESC y Enter
- Devuelve foco al disparador
- Soporte para acciones destructivas

---

## 📦 Tipos TypeScript

```typescript
interface QueuedFile {
  id: string                      // ID único del archivo
  file: File                      // Objeto File del navegador
  status: 'pending' | 'uploading' | 'completed' | 'error'
  progress: number                // Porcentaje 0-100
  error?: string                  // Mensaje de error (si aplica)
  abortController?: AbortController // Para cancelar carga
}

interface UploadOptions {
  maxFileSize?: number            // Límite en bytes
  allowedExtensions?: string[]    // Ej: ['.xlsx', '.xls', '.csv']
  allowedMimeTypes?: string[]     // Tipos MIME permitidos
  maxParallelUploads?: number     // Máximo en paralelo (default: 3)
  endpoint?: string               // URL del servidor (default: '/api/etl/upload')
}

interface FileValidationResult {
  valid: boolean
  error?: string                  // Mensaje si no es válido
}
```

---

## 🔌 Servicio: ETL Upload Service

### Ubicación
`frontend/src/modules/etl/services/etlUploadService.ts`

### Funciones Exportadas

#### `validateETLFile(file, options?): FileValidationResult`
Valida un archivo según reglas de ETL.

```typescript
import { validateETLFile } from '@/modules/etl/services/etlUploadService'

const result = validateETLFile(file, { maxFileSize: 100 * 1024 * 1024 })
if (!result.valid) {
  console.error(result.error)
}
```

#### `uploadFile(file, options?, onProgress?, abortSignal?): Promise<Result>`
Carga un archivo individual.

```typescript
const controller = new AbortController()
const result = await uploadFile(
  file,
  { endpoint: '/api/etl/upload' },
  (progress) => console.log(`${progress}%`),
  controller.signal
)
```

#### `uploadFilesParallel(files, options?, onFileProgress?, onFileComplete?, abortSignal?): Promise<Stats>`
Carga múltiples archivos en paralelo.

```typescript
const stats = await uploadFilesParallel(
  files,
  { maxParallelUploads: 3 },
  (idx, progress) => console.log(`Archivo ${idx}: ${progress}%`),
  (idx, success) => console.log(`Archivo ${idx}: ${success ? 'OK' : 'Error'}`)
)
console.log(`Completados: ${stats.completed}, Fallidos: ${stats.failed}`)
```

#### Utilidades
- `formatFileSize(bytes): string` - Convierte bytes a formato legible
- `generateFileId(): string` - Genera ID único
- `supportsDragAndDrop(): boolean` - Detecta soporte del navegador

---

## 🎨 Diseño Visual & Temas

### Paleta de Colores

| Elemento | Color | Uso |
|----------|-------|-----|
| Primario | `#3498db` | Botones, foco, estados activos |
| Secundario | `#007bff` | Alternativo (si está en uso) |
| Fondo modal | `#ffffff` | Superficie principal |
| Fondo campos | `#f3f4f6` | Superficies secundarias |
| Borde/Divider | `#e5e7eb` | Separadores |
| Texto primario | `#111827` | Encabezados, textos fuertes |
| Texto secundario | `#6b7280` | Subtextos, etiquetas |
| Sidebar | `#262626` | Fondo oscuro |
| Éxito | `#22c55e` | Estados completados |
| Error | `#ef4444` | Estados fallidos |
| Advertencia | `#f59e0b` | Estados en cola |

### Espaciado

| Nivel | Valor |
|-------|-------|
| Modal padding | 32px |
| Modal max-width | 800px |
| Secciones gap | 24px |
| Controles gap | 12px |
| Bordes radius (modal) | 16px |
| Bordes radius (controles) | 8px |
| Botones | 42×42 px |

### Tipografía

```css
Font family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif

Títulos:       24px, 700
Subtítulos:    16px, 600
Cuerpo:        14px, 400
Pequeño:       12px, 400
Etiquetas:     13px, 600
```

---

## ♿ Accesibilidad (WCAG 2.1 AA)

### Implementaciones de WAI-ARIA

#### Modal Dialog
```html
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="modal-title"
  aria-describedby="modal-description"
>
```

**Requisitos:**
- ✅ `role="dialog"` + `aria-modal="true"`
- ✅ Foco inicial en primer control
- ✅ Trampa de foco (Tab/Shift+Tab dentro del modal)
- ✅ ESC cierra (solo si es seguro)
- ✅ Foco devuelto al trigger al cerrar
- ✅ `aria-labelledby` refiere al título
- ✅ `aria-describedby` refiere a descripción

#### Progress Bars
```html
<div
  role="progressbar"
  aria-valuenow="65"
  aria-valuemin="0"
  aria-valuemax="100"
  aria-label="Progreso del archivo: 65%"
></div>
```

**Nota:** Se usa `role="progressbar"` (NO `role="meter"`)

#### Dropzone
```html
<div
  role="region"
  aria-label="Zona para subir archivos de Excel"
>
```

#### Alerts & Status
```html
<div role="alert" aria-live="polite">Error: Archivo demasiado grande</div>
<div role="status" aria-live="polite">Archivo agregado a la cola</div>
```

### Pruebas de Accesibilidad

1. **Navegación por teclado:**
   - [x] Tab/Shift+Tab circula dentro del modal
   - [x] ESC cierra el modal (cuando es seguro)
   - [x] Enter activa botones
   - [x] Espacio activa botones y dropzone
   - [x] Flechas (si hay selectores)

2. **Lector de pantalla (NVDA, JAWS, VoiceOver):**
   - [x] Anuncio de título y descripción
   - [x] Anuncio de cambios de estado
   - [x] Anuncio de errores
   - [x] Anuncio de progreso

3. **Zoom (hasta 200%):**
   - [x] Interfaz legible sin scroll horizontal
   - [x] Botones accesibles sin mezcla

4. **Alto contraste:**
   - [x] Ratio de contraste >= 4.5:1 (WCAG AA)
   - [x] Bordes visibles en modo alto contraste

5. **Color no único:**
   - [x] Estados no se comunican solo con color (usa iconos, texto)

---

## 🚀 Integración en Sidebar

El botón de "Actualización ETL" se encuentra en la barra lateral inferior junto a "Notificaciones" y "Reportes".

### HTML agregado:

```html
<button 
  ref="etlButtonRef"
  class="navbar-icon-btn" 
  title="Actualización ETL" 
  @click="showETLModal = true"
  aria-label="Abrir diálogo de carga de archivos para actualizar ETL"
>
  <svg><!-- Ícono de subida --></svg>
</button>

<ETLUploadModal 
  :is-open="showETLModal" 
  @close="handleETLModalClose"
/>
```

### Comportamiento:
1. Usuario hace clic en botón de sidebar
2. Modal se abre con foco en el título
3. Al cerrar, foco vuelve al botón
4. Si hay errores, se solicita confirmación

---

## 📡 Integración con Backend

### Endpoint esperado

**POST** `/api/etl/upload`

**Request:**
```
Content-Type: multipart/form-data

file: <binary>
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Archivo procesado correctamente",
  "data": {
    "fileId": "abc123",
    "fileName": "datos_etl.xlsx",
    "rowsProcessed": 1250,
    "rowsWithErrors": 3,
    "errors": [
      { "row": 10, "message": "Valor inválido en columna A" }
    ]
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Formato de archivo inválido"
}
```

### Configuración

Para cambiar el endpoint, modifica en **ETLUploadModal.vue**:

```typescript
const uploadFile = async (queuedFile: QueuedFile) => {
  const endpoint = '/api/etl/upload' // ← Cambia aquí
  // ...
}
```

O pasa como prop al servicio:

```typescript
const result = await uploadFile(file, { 
  endpoint: '/tu/endpoint/personalizado'
})
```

---

## 🧪 Pruebas Recomendadas

### Pruebas Unitarias

```typescript
// Validación de archivos
test('rechaza archivos con extensión no permitida', () => {
  const file = new File([''], 'test.pdf')
  const result = validateETLFile(file)
  expect(result.valid).toBe(false)
})

test('rechaza archivos mayores al límite', () => {
  const largeFile = new File(
    [new ArrayBuffer(60 * 1024 * 1024)], 
    'test.xlsx'
  )
  const result = validateETLFile(largeFile)
  expect(result.valid).toBe(false)
})
```

### Pruebas de Integración

- [x] Drag & drop de archivos válidos
- [x] Drag & drop de archivos inválidos
- [x] Selección mediante diálogo de archivos
- [x] Progreso de carga
- [x] Cancelación de carga
- [x] Confirmación de cancelación
- [x] Manejo de errores

### Pruebas de Accesibilidad

- [x] NVDA: Anuncios de estado
- [x] JAWS: Navegación de modal
- [x] VoiceOver (Mac): Focus management
- [x] Teclado: Tab, Shift+Tab, ESC, Enter
- [x] Zoom 200%
- [x] Alto contraste

---

## 🐛 Solución de Problemas

### El modal no aparece
**Causa:** `showETLModal` no se actualiza
**Solución:** Asegúrate de que el binding `:is-open="showETLModal"` es correcto

### Los archivos no se cargan
**Causa:** Endpoint incorrecto o servidor no responde
**Solución:** Verifica la consola (DevTools > Network) y el endpoint en el servicio

### Drag & Drop no funciona
**Causa:** Navegador no soporta FileReader o FormData
**Solución:** Usa `supportsDragAndDrop()` para verificar soporte

### Foco atrapado en modal
**Causa:** No hay trampa de foco implementada
**Solución:** Ya está implementada; verifica que Modal tenga `focus-trap` correcto

---

## 📝 Checklist de Implementación

- [x] Crear estructura de carpetas `modules/etl/`
- [x] Implementar `ETLUploadModal.vue`
- [x] Implementar `UploadDropzone.vue`
- [x] Implementar `FileQueueItem.vue`
- [x] Implementar `ConfirmationDialog.vue`
- [x] Crear `etlUploadService.ts`
- [x] Integrar botón en `Sidebar.vue`
- [x] Validación de archivos
- [x] Progreso visual
- [x] Manejo de errores
- [x] Accesibilidad ARIA
- [x] Gestión de teclado
- [x] Confirmación antes de cancelar
- [x] Respuesta visual (feedback)
- [x] Documentación

---

## 📚 Referencias Normativas

- **W3C Dialog Pattern:** https://www.w3.org/WAI/ARIA/apg/patterns/dialogmodal/
- **MDN Drag & Drop:** https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API
- **MDN Progress Bar:** https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/progressbar_role
- **Material Design Dialogs:** https://m3.material.io/components/dialogs
- **USWDS File Input:** https://designsystem.digital.gov/components/file-input/
- **WCAG 2.1:** https://www.w3.org/WAI/WCAG21/quickref/

---

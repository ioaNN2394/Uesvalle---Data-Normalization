# Explicación del Funcionamiento del Mapa Frontend

Este documento detalla la implementación y el funcionamiento del mapa interactivo visible en el frontend de la aplicación.

## 1. Tecnologías Utilizadas

El mapa está construido sobre una base tecnológica moderna utilizando las siguientes librerías:

- **Vue.js 3:** Es el framework principal sobre el que está construida toda la interfaz de usuario. Se utiliza la API de Composición (`<script setup>`).
- **Leaflet.js:** Es una potente librería de código abierto para mapas interactivos. Se encarga de renderizar el mapa, las capas de tiles, los marcadores y la gestión de eventos.
- **vue-leaflet:** Aunque está listado en las dependencias, la implementación actual en `MapView.vue` opta por importar y usar Leaflet de forma dinámica y directa para un mayor control sobre el ciclo de vida del mapa.

## 2. Arquitectura de Componentes

La funcionalidad del mapa está encapsulada en dos componentes principales:

1.  `frontend/src/pages/MapPage.vue`: Actúa como la página o vista que el enrutador (`vue-router`) muestra al usuario. Su única responsabilidad es cargar el componente principal del mapa.
2.  `frontend/src/modules/map/components/MapView.vue`: Este es el componente central que contiene toda la lógica y la presentación del mapa.

## 3. Funcionamiento del Componente Principal (`MapView.vue`)

Este componente es el corazón de la visualización del mapa. A continuación se describe su funcionamiento interno.

### a. Inicialización del Mapa

-   Cuando el componente se "monta" en la página (usando el hook `onMounted`), se ejecuta la función `initMap`.
-   Esta función importa dinámicamente la librería `Leaflet` y sus estilos CSS.
-   Crea una instancia del mapa y la asocia a un elemento `div` en la plantilla.
-   El mapa se centra en una vista general del Valle del Cauca (`center: [3.8, -76.3]`) con un nivel de zoom inicial.

### b. Capa Base (Tiles)

-   Para el fondo visual del mapa, se utiliza una capa de "tiles" (teselas) de **OpenStreetMap**. Esta es una fuente de datos de mapas gratuita y de código abierto.

### c. Datos y Marcadores (Instituciones)

-   **Fuente de Datos:** Actualmente, el mapa **utiliza una lista de datos de prueba (`mockInstitutions`)** que está definida directamente dentro del archivo `MapView.vue`. Esta lista simula un conjunto de instituciones educativas con su nombre, latitud, longitud, tipo y municipio.
-   **Creación de Marcadores:**
    -   El componente itera sobre esta lista de instituciones.
    -   Para cada institución, crea un marcador (`L.marker`) en su respectiva ubicación geográfica.
    -   Se utiliza un **ícono personalizado (`customIcon`)** para mostrar los marcadores como pequeños puntos de color vino, logrando una apariencia limpia y densa como se requiere.
-   **Popups Interactivos:** Cada marcador tiene asociado un `popup` que se muestra al hacer clic. Este popup presenta información detallada de la institución: nombre, tipo, municipio y coordenadas.

### d. Elementos de Interfaz y UX

-   **Visualizador de Coordenadas:** En la esquina inferior izquierda, una caja muestra las coordenadas geográficas del cursor del ratón en tiempo real.
-   **Control de Escala:** Se añade un control de escala de Leaflet en la parte inferior izquierda para dar referencia de las distancias en el mapa.
-   **Estilos Personalizados:** El archivo contiene estilos CSS (`<style>`) que personalizan la apariencia de los marcadores, los popups y otros elementos del mapa para que se integren con el diseño de la aplicación.

## 4. Flujo de Datos Actual y Futuro

Actualmente, el flujo de datos es **estático**. El componente es autosuficiente y no depende de una fuente de datos externa.

Para una implementación de producción, el siguiente paso sería modificar el componente para que, en lugar de usar `mockInstitutions`, realice una petición a una API del backend para obtener la lista de instituciones y la muestre dinámicamente en el mapa.

## 5. Resumen de Archivos Clave

-   `frontend/package.json`: Define las dependencias (`leaflet`, `vue-leaflet`).
-   `frontend/src/pages/MapPage.vue`: Contenedor de la vista del mapa.
-   `frontend/src/modules/map/components/MapView.vue`: Implementación principal y lógica del mapa.

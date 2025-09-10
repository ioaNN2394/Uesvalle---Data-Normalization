<template>
  <footer class="map-footer">
    <div class="footer-left">
      <!-- Las coordenadas ya están en el mapa -->
    </div>
    <div class="footer-right">
      <span class="attribution">
        Data © OpenStreetMap contributors, Microsoft, Facebook, Inc. and its affiliates, Esri Community Maps contributors
      </span>
      <span class="powered-by">Powered by Vue 3 & Leaflet</span>
    </div>
  </footer>
</template>

<script setup lang="ts">
// No necesitamos lógica aquí por ahora
</script>

<style scoped>
.map-footer {
  height: 30px;
  background: rgba(255, 255, 255, 0.9);
  border-top: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  font-size: 11px;
  color: #666;
  z-index: 1000;
}

.footer-right {
  display: flex;
  gap: 20px;
  align-items: center;
}

.attribution {
  font-size: 10px;
}

.powered-by {
  font-weight: 500;
  color: #3498db;
}
</style>

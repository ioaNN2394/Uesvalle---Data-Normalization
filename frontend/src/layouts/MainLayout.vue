<template>
  <div class="main-layout">
    <AppHeader />
    <div class="content-container">
      <Sidebar />
      <div class="map-container">
        <router-view />
      </div>
    </div>
    <MapFooter />
  </div>
</template>

<script setup lang="ts">
import AppHeader from '../components/AppHeader.vue'
import Sidebar from '../components/Sidebar.vue'
import MapFooter from '../components/MapFooter.vue'
</script>

<style scoped>
.main-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-container {
  flex: 1;
  display: flex;
  position: relative;
}

.map-container {
  flex: 1;
  position: relative;
}
</style>

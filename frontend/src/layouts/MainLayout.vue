<template>
  <div class="main-layout">
    <AppHeader />
    <div class="content-container">
      <Sidebar />
      <div class="map-container">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from '../components/AppHeader.vue'
import Sidebar from '../components/Sidebar.vue'
</script>

<style scoped>
.main-layout {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  overflow: hidden;
}

.content-container {
  flex: 1;
  display: flex;
  position: relative;
  height: calc(100vh - 70px);
  overflow: hidden;
}

.map-container {
  flex: 1;
  position: relative;
  height: 100%;
  overflow: hidden;
}
</style>
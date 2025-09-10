<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo-section">
        <img src="/logo-uesvalle.png" alt="UesValle Logo" class="logo" />
        <h1 class="title">GeoVisor Instituciones Educativas UesValle</h1>
      </div>
    </div>
    
    <div class="header-center">
      <div class="search-container">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Buscar Instituciones..."
          class="search-input"
          @keyup.enter="handleSearch"
        />
        <button @click="handleSearch" class="search-button">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
        </button>
      </div>
    </div>
    
    
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const searchQuery = ref('')

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    console.log('Searching for:', searchQuery.value)
    // TODO: Implementar lógica de búsqueda
  }
}
</script>

<style scoped>
.app-header {
  height: 70px;
  background: #262626;
 
  display: flex;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  position: relative;
}

.header-left {
  flex: 0 0 auto;
  min-width: 300px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
  
}

.logo {
  height: 45px;
  width: auto;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
  white-space: nowrap;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 0 40px;
}

.search-container {
  position: relative;
  width: 100%;
  max-width: 500px;
}

.search-input {
  width: 100%;
  height: 45px;
  padding: 0 50px 0 20px;
  border: 2px solid #ddd;
  border-radius: 25px;
  font-size: 15px;
  outline: none;
  transition: all 0.3s ease;
  background: #f8f9fa;
}

.search-input:focus {
  border-color: #007bff;
  background: white;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.search-button {
  position: absolute;
  right: 5px;
  top: 50%;
  transform: translateY(-50%);
  background: #007bff;
  border: none;
  border-radius: 50%;
  width: 35px;
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: white;
  transition: background-color 0.3s ease;
}

.search-button:hover {
  background: #0056b3;
}

.header-right {
  flex: 0 0 auto;
  min-width: 120px;
}

.header-icons {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}

.header-icon-btn {
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

.header-icon-btn:hover {
  background: #f0f0f0;
}

.header-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
}
</style>
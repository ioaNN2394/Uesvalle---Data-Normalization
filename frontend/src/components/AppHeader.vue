<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo-section">
        <img src="/vite.svg" alt="UesValle Logo" class="logo" />
        <h1 class="title">GeoVisor Instituciones Educativas</h1>
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
          <Search :size="20" />
        </button>
      </div>
    </div>
    
    <div class="header-right">
      <!-- Espacio para futuras funcionalidades -->
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search } from 'lucide-vue-next'

const searchQuery = ref<string>('')

const handleSearch = (): void => {
  if (searchQuery.value.trim()) {
    console.log('Searching for:', searchQuery.value)
    // TODO: Implementar lógica de búsqueda
  }
}
</script>

<style scoped>
.app-header {
  height: 60px;
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 1000;
}

.header-left {
  flex: 1;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  height: 40px;
  width: auto;
}

.title {
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.header-center {
  flex: 2;
  display: flex;
  justify-content: center;
}

.search-container {
  position: relative;
  width: 100%;
  max-width: 400px;
}

.search-input {
  width: 100%;
  height: 40px;
  padding: 0 50px 0 16px;
  border: 2px solid #e0e0e0;
  border-radius: 20px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s ease;
}

.search-input:focus {
  border-color: #3498db;
}

.search-button {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: #3498db;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: white;
  transition: background-color 0.3s ease;
}

.search-button:hover {
  background: #2980b9;
}

.header-right {
  flex: 1;
}
</style>
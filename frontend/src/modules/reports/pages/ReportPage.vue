<template>
  <div class="report-page">
    <div class="report-container">
      <header class="report-header">
        <h1>Módulo de Reportes</h1>
        <p>Esta sección está en construcción.</p>
      </header>
      <main class="report-content">
        <p>Aquí podrás generar y visualizar reportes detallados sobre las instituciones educativas.</p>
        <button @click="goToMap" class="back-button">Volver al Mapa</button>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';

const router = useRouter();

const goToMap = () => {
  router.push({ name: 'map' });
};
</script>

<style scoped>
.report-page {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #e9ecef;
  padding: 20px;
}

.report-container {
  max-width: 600px;
  width: 100%;
  padding: 40px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  text-align: center;
}

.report-header h1 {
  color: #343a40;
  font-size: 2em;
  margin-bottom: 10px;
}

.report-header p {
  color: #6c757d;
  font-size: 1.1em;
}

.report-content {
  margin-top: 30px;
}

.back-button {
  margin-top: 25px;
  padding: 10px 20px;
  font-size: 1em;
  color: #fff;
  background-color: #007bff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.back-button:hover {
  background-color: #0056b3;
}
</style>
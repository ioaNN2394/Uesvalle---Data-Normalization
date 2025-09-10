<template>
  <router-view />
</template>

<script setup lang="ts">
// No necesitamos importar nada aquí, el router-view se encarga de todo
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f5f5f5;
}

#app {
  height: 100vh;
}
</style>

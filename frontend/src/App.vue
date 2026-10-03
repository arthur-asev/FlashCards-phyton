<script setup lang="ts">
import { ref } from "vue";

const message = ref("Ambiente inicial pronto.");
</script>

<template>
  <main>
    <h1>Flashcard Platform</h1>
    <p>{{ message }}</p>
    <p>Próximo módulo: upload e preview de planilhas.</p>
  </main>
</template>

<style>
body {
  margin: 0;
  font-family: Arial, sans-serif;
}
main {
  max-width: 900px;
  margin: 80px auto;
  padding: 24px;
}
</style>

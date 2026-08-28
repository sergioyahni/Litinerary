<template>
  <AppLayout>
    <AuthBootstrap />
    <RouterView />
  </AppLayout>
</template>

<script setup lang="ts">
import AuthBootstrap from "./components/auth/AuthBootstrap.vue";
import AppLayout from "./components/layout/AppLayout.vue";
</script>

<template>
  <div class="site-shell">
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <AppHeader />
    <main id="main-content" tabindex="-1">
      <slot />
    </main>
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import AppFooter from "./AppFooter.vue";
import AppHeader from "./AppHeader.vue";
</script>

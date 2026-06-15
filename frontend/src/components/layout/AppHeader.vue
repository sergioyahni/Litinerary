<template>
  <header class="header-area">
    <div class="main-menu">
      <div class="nav-container">
        <RouterLink class="brand-link" :to="{ name: 'home' }" aria-label="Litinerary home">
          <img :src="logoUrl" height="50" alt="Litinerary" />
        </RouterLink>

        <button
          class="nav-toggle"
          type="button"
          :aria-expanded="isOpen"
          aria-controls="main-navigation"
          aria-label="Open or close main navigation"
          @click="isOpen = !isOpen"
        >
          <span />
          <span />
          <span />
        </button>

        <div id="main-navigation" class="nav-panel" :class="{ 'is-open': isOpen }">
          <MainNavigation @navigate="isOpen = false" />
          <RouterLink class="button nav-cta" :to="{ name: 'destinations' }" @click="isOpen = false">
            Start Planning
          </RouterLink>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from "vue";
import MainNavigation from "./MainNavigation.vue";
import logoUrl from "../../assets/template/logo.png";

const isOpen = ref(false);
</script>

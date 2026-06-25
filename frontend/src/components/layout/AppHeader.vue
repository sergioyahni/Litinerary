<template>
  <header class="header-area">
    <div class="main-menu">
      <div class="nav-container">
        <RouterLink
          class="brand-link"
          :to="{ name: 'home' }"
          aria-label="Litinerary home"
        >
          <img :src="logoUrl" alt="Litinerary" />
          <span class="brand-name">Litinerary</span>
        </RouterLink>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import logoUrl from "../../assets/template/logo_img.png";
</script>
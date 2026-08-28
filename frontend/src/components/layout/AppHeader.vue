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
        <div class="nav-panel">
          <MainNavigation />
          <div class="auth-actions">
            <span v-if="authStore.isInitializing" class="auth-status" aria-live="polite">
              Checking session
            </span>
            <span v-else-if="authStore.isAuthenticated" class="auth-status">
              {{ authStore.currentUser?.displayName ?? authStore.currentUserId }}
            </span>
            <button
              v-if="authStore.isAuthEnabled && !authStore.isAuthenticated"
              class="button compact-button"
              type="button"
              @click="authStore.login($route.fullPath)"
            >
              Sign In
            </button>
            <button
              v-else-if="authStore.isAuthenticated"
              class="button compact-button secondary-button"
              type="button"
              @click="authStore.logout"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import logoUrl from "../../assets/template/logo_img.png";
import { useAuthStore } from "../../stores/authStore";
import MainNavigation from "./MainNavigation.vue";

const authStore = useAuthStore();
</script>

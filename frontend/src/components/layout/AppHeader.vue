<template>
  <header class="header-area">
    <div class="main-menu">
      <div class="nav-container">
        <RouterLink
          class="brand-link"
          :to="{ name: 'home' }"
          aria-label="Litinerary home"
          @click="closeMenu"
        >
          <img :src="logoUrl" alt="Litinerary" />
          <span class="brand-name">Litinerary</span>
        </RouterLink>
        <div ref="menuRoot" class="nav-menu">
          <button
            ref="menuButton"
            class="nav-toggle"
            :class="{ 'is-open': isMenuOpen }"
            type="button"
            aria-controls="main-navigation-panel"
            :aria-expanded="isMenuOpen"
            :aria-label="isMenuOpen ? 'Close navigation menu' : 'Open navigation menu'"
            @click="toggleMenu"
          >
            <span aria-hidden="true"></span>
            <span aria-hidden="true"></span>
            <span aria-hidden="true"></span>
          </button>
          <div v-if="isMenuOpen" id="main-navigation-panel" class="nav-panel">
            <MainNavigation @navigate="closeMenu" />
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
    </div>
  </header>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

import logoUrl from "../../assets/template/logo_img.png";
import { useAuthStore } from "../../stores/authStore";
import MainNavigation from "./MainNavigation.vue";

const authStore = useAuthStore();
const isMenuOpen = ref(false);
const menuButton = ref<HTMLButtonElement | null>(null);
const menuRoot = ref<HTMLElement | null>(null);

function closeMenu(): void {
  isMenuOpen.value = false;
}

function toggleMenu(): void {
  isMenuOpen.value = !isMenuOpen.value;
}

function handleDocumentClick(event: MouseEvent): void {
  if (isMenuOpen.value && !menuRoot.value?.contains(event.target as Node)) {
    closeMenu();
  }
}

function handleDocumentKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && isMenuOpen.value) {
    closeMenu();
    menuButton.value?.focus();
  }
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleDocumentKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleDocumentKeydown);
});
</script>

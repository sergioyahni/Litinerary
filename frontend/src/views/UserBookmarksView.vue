<template>
  <section class="page-banner">
    <div class="container">
      <h1>Bookmarks</h1>
      <p>Routes saved to your Litinerary account.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div v-if="authStore.isAuthEnabled && !authStore.isAuth0Configured" class="placeholder-panel error-panel">
        <h2>Authentication is not configured</h2>
        <p>{{ authStore.error ?? "Auth0 frontend configuration is incomplete." }}</p>
      </div>

      <div v-else-if="authStore.isAuthEnabled && !authStore.isAuthenticated" class="placeholder-panel">
        <h2>Sign in to view bookmarks</h2>
        <p>Saved routes are available after your session is verified.</p>
        <button class="button compact-button" type="button" @click="authStore.login('/account/bookmarks')">
          Sign In
        </button>
      </div>

      <div v-else-if="userStore.isLoading" class="placeholder-panel" aria-live="polite">
        <p class="loading-note">Loading bookmarks...</p>
      </div>

      <div v-else-if="userStore.error" class="placeholder-panel error-panel" role="alert">
        <h2>Bookmarks could not load</h2>
        <p>{{ userStore.error }}</p>
        <button class="button compact-button" type="button" @click="userStore.loadBookmarks">
          Try Loading Bookmarks Again
        </button>
      </div>

      <div v-else-if="userStore.bookmarks.length === 0" class="placeholder-panel">
        <h2>No bookmarks yet</h2>
        <p>Open an itinerary and use the bookmark button to save it to the development profile.</p>
        <RouterLink class="button compact-button" :to="{ name: 'itinerary-repository' }">
          Browse Public Repository
        </RouterLink>
      </div>

      <div v-else class="data-card-grid">
        <article v-for="itinerary in userStore.bookmarks" :key="itinerary.id" class="data-card">
          <p class="eyebrow">{{ itinerary.transportationMode.replace("_", " ") }}</p>
          <h2>{{ itinerary.title }}</h2>
          <p>{{ itinerary.summary }}</p>
          <RouterLink
            class="button compact-button"
            :to="{ name: 'itinerary-detail', params: { id: itinerary.id } }"
          >
            Open {{ itinerary.title }}
          </RouterLink>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useAuthStore } from "../stores/authStore";
import { useUserStore } from "../stores/userStore";

const authStore = useAuthStore();
const userStore = useUserStore();

onMounted(() => {
  void userStore.loadBookmarks();
});
</script>

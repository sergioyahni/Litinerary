<template>
  <section class="page-banner">
    <div class="container">
      <h1>Bookmarks</h1>
      <p>Routes saved by the temporary development user.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div v-if="userStore.isLoading" class="placeholder-panel" aria-live="polite">
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
import { useUserStore } from "../stores/userStore";

const userStore = useUserStore();

onMounted(() => {
  void userStore.loadBookmarks();
});
</script>

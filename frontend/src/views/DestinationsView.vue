<template>
  <section class="page-banner">
    <div class="container">
      <h1>Choose a Destination</h1>
      <p>Start the MVP flow by selecting one of the supported literary cities.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div v-if="destinationStore.isLoading" class="placeholder-panel" aria-live="polite">
        <p class="loading-note">Loading destinations...</p>
      </div>

      <div v-else-if="destinationStore.error" class="placeholder-panel error-panel" role="alert">
        <h2>Destinations could not load</h2>
        <p>{{ destinationStore.error }}</p>
        <button class="button compact-button" type="button" @click="destinationStore.loadDestinations">
          Try Loading Destinations Again
        </button>
      </div>

      <div v-else-if="destinationStore.destinations.length === 0" class="placeholder-panel">
        <h2>No destinations yet</h2>
        <p>The mock catalog is empty. Add supported cities to the backend mock data to continue.</p>
      </div>

      <div v-else class="data-card-grid">
        <article
          v-for="destination in destinationStore.destinations"
          :key="destination.id"
          class="data-card"
        >
          <p class="eyebrow">{{ destination.country }}</p>
          <h2>{{ destination.name }}</h2>
          <p>{{ destination.description }}</p>
          <RouterLink
            class="button compact-button"
            :to="{ name: 'destination-books', params: { destinationId: destination.id } }"
            @click="destinationStore.selectDestination(destination.id)"
          >
            View Books for {{ destination.name }}
          </RouterLink>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useDestinationStore } from "../stores/destinationStore";

const destinationStore = useDestinationStore();

onMounted(() => {
  if (destinationStore.destinations.length === 0) {
    void destinationStore.loadDestinations();
  }
});
</script>

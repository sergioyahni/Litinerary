<template>
  <section class="page-banner">
    <div class="container">
      <h1>Choose a Destination</h1>
      <p>Select one of the supported literary cities.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <form
        v-if="authStore.canUseExternalDiscovery"
        class="discovery-form"
        aria-label="Discover destinations beyond the public repository"
        @submit.prevent="discoverDestinations"
      >
        <label for="destination-discovery-query">Find another destination</label>
        <div class="discovery-form-row">
          <input
            id="destination-discovery-query"
            v-model="discoveryQuery"
            autocomplete="off"
            placeholder="Search by city or country"
            required
            type="search"
          />
          <button
            class="button compact-button"
            :disabled="destinationStore.isLoading || !discoveryQuery.trim()"
            type="submit"
          >
            Search
          </button>
        </div>
      </form>

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
import { onMounted, ref } from "vue";
import { useAuthStore } from "../stores/authStore";
import { useDestinationStore } from "../stores/destinationStore";

const authStore = useAuthStore();
const destinationStore = useDestinationStore();
const discoveryQuery = ref("");

function discoverDestinations(): void {
  const query = discoveryQuery.value.trim();
  if (query && authStore.canUseExternalDiscovery) {
    void destinationStore.discoverMissingDestinations(query);
  }
}

onMounted(() => {
  if (destinationStore.destinations.length === 0) {
    void destinationStore.loadDestinations();
  }
});
</script>

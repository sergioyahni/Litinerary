<template>
  <section class="page-banner">
    <div class="container">
      <h1>Public Litineraries</h1>
      <p>Browse reusable mock routes, including exact matches and adapted itineraries.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div v-if="repositoryStore.isLoading" class="placeholder-panel" aria-live="polite">
        <p class="loading-note">Loading public itineraries...</p>
      </div>

      <div v-else-if="repositoryStore.error" class="placeholder-panel error-panel" role="alert">
        <h2>Repository could not load</h2>
        <p>{{ repositoryStore.error }}</p>
        <button class="button compact-button" type="button" @click="repositoryStore.loadItineraries">
          Try Loading Repository Again
        </button>
      </div>

      <div v-else-if="repositoryStore.itineraries.length === 0" class="placeholder-panel">
        <h2>No public itineraries yet</h2>
        <p>Generate an itinerary to add mock routes to the public repository for this running session.</p>
        <RouterLink class="button compact-button" :to="{ name: 'destinations' }">
          Start Planning
        </RouterLink>
      </div>

      <div v-else class="data-card-grid">
        <article
          v-for="itinerary in repositoryStore.itineraries"
          :key="itinerary.id"
          class="data-card"
        >
          <p class="eyebrow">
            {{ itinerary.transportationMode.replace("_", " ") }} -
            {{ itinerary.durationDays }} day{{ itinerary.durationDays === 1 ? "" : "s" }}
          </p>
          <h2>{{ itinerary.title }}</h2>
          <p>{{ itinerary.summary }}</p>
          <p v-if="itinerary.sourceType" class="source-chip">
            {{ itinerary.sourceType.replace(/_/g, " ") }}
          </p>
          <p v-if="itinerary.adaptationNotes?.length" class="muted">
            {{ itinerary.adaptationNotes[0] }}
          </p>
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
import { useItineraryRepositoryStore } from "../stores/itineraryRepositoryStore";

const repositoryStore = useItineraryRepositoryStore();

onMounted(() => {
  void repositoryStore.loadItineraries();
});
</script>

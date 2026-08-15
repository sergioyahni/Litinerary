<template>
  <section class="page-banner">
    <div class="container">
      <h1>Itinerary Detail</h1>
      <p>Review an accessible route and its text alternative to the map.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div v-if="repositoryStore.isLoading" class="placeholder-panel" aria-live="polite">
        <p class="loading-note">Loading itinerary {{ itineraryId }}...</p>
      </div>

      <div v-else-if="repositoryStore.error" class="placeholder-panel error-panel" role="alert">
        <h2>Itinerary could not load</h2>
        <p>{{ repositoryStore.error }}</p>
        <button class="button compact-button" type="button" @click="loadDetail">
          Try Loading Itinerary Again
        </button>
      </div>

      <div v-else-if="!repositoryStore.selectedItinerary" class="placeholder-panel">
        <h2>Itinerary not found</h2>
        <p>This route is not available in the current mock repository.</p>
        <RouterLink class="button compact-button" :to="{ name: 'itinerary-repository' }">
          Browse Public Repository
        </RouterLink>
      </div>

      <article v-else class="itinerary-detail">
        <ItinerarySummary :itinerary="repositoryStore.selectedItinerary" />
        <ItineraryMap :itinerary="repositoryStore.selectedItinerary" />
        <ItineraryNarration :itinerary="repositoryStore.selectedItinerary" />
        <ItineraryAccountPanel :itinerary="repositoryStore.selectedItinerary" />
        <h2 class="section-heading">Text Itinerary</h2>
        <ItineraryDayList :days="repositoryStore.selectedItinerary.days" />
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import ItineraryAccountPanel from "../components/itinerary/ItineraryAccountPanel.vue";
import ItineraryDayList from "../components/itinerary/ItineraryDayList.vue";
import ItineraryNarration from "../components/itinerary/ItineraryNarration.vue";
import ItinerarySummary from "../components/itinerary/ItinerarySummary.vue";
import ItineraryMap from "../components/map/ItineraryMap.vue";
import { useItineraryRepositoryStore } from "../stores/itineraryRepositoryStore";

const route = useRoute();
const repositoryStore = useItineraryRepositoryStore();

const itineraryId = computed(() => {
  const param = route.params.id;
  return typeof param === "string" ? param : "";
});

function loadDetail(): void {
  void repositoryStore.loadItineraryDetail(itineraryId.value);
}

onMounted(loadDetail);
watch(itineraryId, loadDetail);
</script>

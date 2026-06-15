<template>
  <section class="page-banner">
    <div class="container">
      <h1>Your Generated Litinerary</h1>
      <p>Review the route summary, mapped stops, and text itinerary before using it as travel inspiration.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div v-if="!itineraryStore.currentItinerary" class="placeholder-panel">
        <h2>No generated itinerary yet</h2>
        <p>Complete the destination, book, and configuration steps to create an MVP itinerary.</p>
        <RouterLink class="button compact-button" :to="{ name: 'destinations' }">
          Start Planning
        </RouterLink>
      </div>

      <div v-else-if="!itineraryStore.hasValidItinerary" class="placeholder-panel error-panel" role="alert">
        <h2>Generated itinerary is incomplete</h2>
        <p>The route did not include displayable day and stop data. Try generating it again.</p>
        <RouterLink class="button compact-button" :to="{ name: 'destinations' }">
          Start Again
        </RouterLink>
      </div>

      <article v-else class="itinerary-detail">
        <ItinerarySummary :itinerary="itineraryStore.currentItinerary" />

        <p v-if="itineraryStore.lastResponse" class="status-note">
          {{ itineraryStore.lastResponse.message }}
        </p>

        <ItineraryMap :itinerary="itineraryStore.currentItinerary" />
        <ItineraryNarration :itinerary="itineraryStore.currentItinerary" />
        <ItineraryAccountPanel :itinerary="itineraryStore.currentItinerary" />
        <h2 class="section-heading">Text Itinerary</h2>
        <ItineraryDayList :days="itineraryStore.currentItinerary.days" />
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import ItineraryDayList from "../components/itinerary/ItineraryDayList.vue";
import ItineraryAccountPanel from "../components/itinerary/ItineraryAccountPanel.vue";
import ItineraryNarration from "../components/itinerary/ItineraryNarration.vue";
import ItinerarySummary from "../components/itinerary/ItinerarySummary.vue";
import ItineraryMap from "../components/map/ItineraryMap.vue";
import { useItineraryStore } from "../stores/itineraryStore";

const itineraryStore = useItineraryStore();
</script>

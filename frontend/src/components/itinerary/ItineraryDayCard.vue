<template>
  <article class="itinerary-day-card">
    <div class="day-card-header">
      <div>
        <p class="eyebrow">Day {{ day.dayNumber }}</p>
        <h3>{{ day.title }}</h3>
      </div>
      <div class="day-meta">
        <span v-if="day.estimatedDurationHours">{{ day.estimatedDurationHours }} hr</span>
        <span v-if="day.estimatedDistanceKm">{{ day.estimatedDistanceKm }} km</span>
      </div>
    </div>

    <p>{{ day.summary }}</p>

    <div v-if="day.stops.length === 0" class="placeholder-panel">
      <p>No stops are available for this day.</p>
    </div>

    <div v-else class="stop-card-list" aria-label="Stops for this day">
      <ItineraryStopCard v-for="stop in day.stops" :key="stop.id" :stop="stop" />
    </div>
  </article>
</template>

<script setup lang="ts">
import type { ItineraryDay } from "../../types";
import ItineraryStopCard from "./ItineraryStopCard.vue";

defineProps<{
  day: ItineraryDay;
}>();
</script>

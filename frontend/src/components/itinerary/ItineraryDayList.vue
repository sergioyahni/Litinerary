<template>
  <div class="itinerary-day-list">
    <div v-if="days.length === 0" class="placeholder-panel">
      <p>No itinerary days are available.</p>
    </div>

    <ItineraryDayCard v-for="day in days" v-else :key="day.id" :day="day" />
  </div>
</template>

<script setup lang="ts">
import type { ItineraryDay } from "../../types";
import ItineraryDayCard from "./ItineraryDayCard.vue";

defineProps<{
  days: ItineraryDay[];
}>();
</script>

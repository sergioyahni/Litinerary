<template>
  <section class="itinerary-summary">
    <div>
      <p class="eyebrow">Litinerary</p>
      <h2>{{ itinerary.title }}</h2>
      <p>{{ itinerary.summary }}</p>
    </div>

    <dl class="summary-stat-grid">
      <div>
        <dt>Duration</dt>
        <dd>{{ itinerary.durationDays }} day{{ itinerary.durationDays === 1 ? "" : "s" }}</dd>
      </div>
      <div>
        <dt>Transport</dt>
        <dd><TransportModeBadge :mode="itinerary.transportationMode" /></dd>
      </div>
      <div>
        <dt>Stops</dt>
        <dd>{{ stopCount }}</dd>
      </div>
      <div>
        <dt>Source</dt>
        <dd>{{ sourceLabel }}</dd>
      </div>
    </dl>

    <div v-if="itinerary.sourceItineraryId || notes.length > 0" class="source-note-panel">
      <p v-if="itinerary.sourceItineraryId">
        Source itinerary: <strong>{{ itinerary.sourceItineraryId }}</strong>
      </p>
      <ul v-if="notes.length > 0">
        <li v-for="note in notes" :key="note">{{ note }}</li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Itinerary } from "../../types";
import TransportModeBadge from "./TransportModeBadge.vue";

const props = defineProps<{
  itinerary: Itinerary;
}>();

const stopCount = computed(() =>
  props.itinerary.days.reduce((count, day) => count + day.stops.length, 0),
);

const sourceLabel = computed(() =>
  (props.itinerary.sourceType ?? props.itinerary.generatedFrom).replace(/_/g, " "),
);

const notes = computed(() => props.itinerary.adaptationNotes ?? []);
</script>

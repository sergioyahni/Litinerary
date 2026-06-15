<template>
  <article class="itinerary-stop-card">
    <div class="stop-order" aria-label="Stop order">{{ stop.order }}</div>
    <div class="stop-content">
      <div class="stop-heading">
        <div>
          <p class="eyebrow">Stop {{ stop.order }}</p>
          <h4>{{ stop.poi?.name || stop.title || "Unnamed stop" }}</h4>
        </div>
        <span v-if="stop.poi?.estimatedDurationMinutes" class="duration-pill">
          {{ stop.poi.estimatedDurationMinutes }} min
        </span>
      </div>

      <p v-if="stop.poi?.description">{{ stop.poi.description }}</p>
      <p v-if="stop.poi?.literaryRelevance" class="literary-relevance">
        {{ stop.poi.literaryRelevance }}
      </p>
      <p v-if="stop.narrativeNote && stop.narrativeNote !== stop.poi?.literaryRelevance">
        {{ stop.narrativeNote }}
      </p>
      <p v-if="stop.logisticsNote" class="muted">{{ stop.logisticsNote }}</p>
      <TicketingNote
        v-if="stop.poi?.ticketingNote || stop.poi?.ticketingUrl"
        :note="stop.poi.ticketingNote ?? undefined"
        :url="stop.poi.ticketingUrl"
      />
      <p v-if="coordinateLabel" class="coordinate-note">{{ coordinateLabel }}</p>
      <p v-else class="coordinate-note missing">Coordinates unavailable for this stop.</p>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ItineraryStop } from "../../types";
import TicketingNote from "./TicketingNote.vue";

const props = defineProps<{
  stop: ItineraryStop;
}>();

const coordinateLabel = computed(() => {
  const latitude = props.stop.poi?.latitude;
  const longitude = props.stop.poi?.longitude;

  if (
    typeof latitude !== "number" ||
    typeof longitude !== "number" ||
    Number.isNaN(latitude) ||
    Number.isNaN(longitude)
  ) {
    return "";
  }

  return `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
});
</script>

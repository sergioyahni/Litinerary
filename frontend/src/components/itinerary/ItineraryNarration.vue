<template>
  <section class="narration-panel" aria-labelledby="narration-heading">
    <div class="narration-header">
      <div>
        <p class="eyebrow">Audio Guide</p>
        <h2 id="narration-heading">Narration</h2>
      </div>
      <button
        class="button compact-button"
        type="button"
        :disabled="isLoading"
        @click="loadNarration({ includePlaceholderAudio: true })"
      >
        {{ isLoading ? "Preparing..." : "Prepare Narration" }}
      </button>
    </div>

    <p v-if="error" class="status-note" role="status">
      {{ error }}
    </p>

    <div v-if="showPlaceholderAudio" class="placeholder-audio">
      <audio :src="narration?.audio.url ?? undefined" controls preload="none">
        Audio playback is not available in this browser.
      </audio>
      <p>Placeholder audio metadata only. Use the text narration below.</p>
    </div>

    <div class="narration-text">
      <h3>{{ narrationTitle }}</h3>
      <p>{{ narrationText }}</p>
    </div>

    <ul v-if="audioWarnings.length > 0" class="narration-warnings">
      <li v-for="warning in audioWarnings" :key="warning">{{ warning }}</li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  fetchItineraryNarration,
  generateItineraryNarration,
} from "../../services/itinerariesApi";
import type { Itinerary, ItineraryNarration, NarrationRequest } from "../../types";

const props = defineProps<{
  itinerary: Itinerary;
}>();

const narration = ref<ItineraryNarration | null>(null);
const isLoading = ref(false);
const error = ref<string | null>(null);

const fallbackText = computed(() => {
  const daySummaries = props.itinerary.days
    .map((day) => `Day ${day.dayNumber}: ${day.title}. ${day.summary}`)
    .join(" ");
  return `${props.itinerary.title}. ${props.itinerary.summary} ${daySummaries}`.trim();
});

const narrationTitle = computed(
  () => narration.value?.script.title ?? `Narration for ${props.itinerary.title}`,
);

const narrationText = computed(() => narration.value?.script.text ?? fallbackText.value);

const showPlaceholderAudio = computed(
  () =>
    narration.value?.audio.available === true &&
    narration.value.audio.placeholder === true &&
    typeof narration.value.audio.url === "string" &&
    narration.value.audio.url.length > 0,
);

const audioWarnings = computed(() => narration.value?.audio.warnings ?? []);

async function loadNarration(request?: NarrationRequest): Promise<void> {
  isLoading.value = true;
  error.value = null;

  try {
    narration.value = request
      ? await generateItineraryNarration(props.itinerary.id, request)
      : await fetchItineraryNarration(props.itinerary.id);
  } catch (caught) {
    narration.value = null;
    error.value =
      caught instanceof Error
        ? `${caught.message} Showing text narration fallback.`
        : "Showing text narration fallback.";
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  void loadNarration();
});

watch(
  () => props.itinerary.id,
  () => {
    narration.value = null;
    void loadNarration();
  },
);
</script>

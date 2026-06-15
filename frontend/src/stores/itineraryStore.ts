import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { generateItinerary } from "../services/itinerariesApi";
import type {
  Itinerary,
  ItineraryGenerationRequest,
  ItineraryGenerationResponse,
  TransportationMode,
} from "../types";

export const useItineraryStore = defineStore("itinerary", () => {
  const currentItinerary = ref<Itinerary | null>(null);
  const lastResponse = ref<ItineraryGenerationResponse | null>(null);
  const durationDays = ref(1);
  const transportationMode = ref<TransportationMode>("walking");
  const isGenerating = ref(false);
  const error = ref<string | null>(null);

  const hasItinerary = computed(() => currentItinerary.value !== null);
  const hasValidItinerary = computed(
    () =>
      currentItinerary.value !== null &&
      currentItinerary.value.days.length > 0 &&
      currentItinerary.value.days.every((day) => day.stops.length > 0),
  );

  async function submitGeneration(
    request: Omit<ItineraryGenerationRequest, "durationDays" | "transportationMode">,
  ): Promise<ItineraryGenerationResponse | null> {
    if (!request.destinationId || !request.bookId) {
      error.value = "Choose a destination and book before generating an itinerary.";
      return null;
    }

    isGenerating.value = true;
    error.value = null;

    try {
      const response = await generateItinerary({
        ...request,
        durationDays: durationDays.value,
        transportationMode: transportationMode.value,
      });
      lastResponse.value = response;
      currentItinerary.value = response.itinerary;
      return response;
    } catch (caught) {
      error.value =
        caught instanceof Error ? caught.message : "Unable to generate itinerary.";
      currentItinerary.value = null;
      lastResponse.value = null;
      return null;
    } finally {
      isGenerating.value = false;
    }
  }

  function setCurrentItinerary(itinerary: Itinerary): void {
    currentItinerary.value = itinerary;
    lastResponse.value = null;
    error.value = null;
  }

  function clearCurrentItinerary(): void {
    currentItinerary.value = null;
    lastResponse.value = null;
    error.value = null;
  }

  function resetConfiguration(): void {
    durationDays.value = 1;
    transportationMode.value = "walking";
    error.value = null;
  }

  function reset(): void {
    currentItinerary.value = null;
    lastResponse.value = null;
    durationDays.value = 1;
    transportationMode.value = "walking";
    isGenerating.value = false;
    error.value = null;
  }

  return {
    currentItinerary,
    lastResponse,
    durationDays,
    transportationMode,
    isGenerating,
    error,
    hasItinerary,
    hasValidItinerary,
    submitGeneration,
    setCurrentItinerary,
    clearCurrentItinerary,
    resetConfiguration,
    reset,
  };
});

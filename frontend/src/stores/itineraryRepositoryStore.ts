import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
  fetchItineraryDetail,
  fetchPublicItineraries,
} from "../services/itinerariesApi";
import type { Itinerary, TransportationMode } from "../types";

interface ExactPublicItineraryCriteria {
  destinationId: string;
  bookId: string;
  durationDays: number;
  transportationMode: TransportationMode;
}

export const useItineraryRepositoryStore = defineStore("itineraryRepository", () => {
  const itineraries = ref<Itinerary[]>([]);
  const selectedItinerary = ref<Itinerary | null>(null);
  const exactMatch = ref<Itinerary | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const hasItineraries = computed(() => itineraries.value.length > 0);

  async function loadItineraries(): Promise<void> {
    isLoading.value = true;
    error.value = null;

    try {
      itineraries.value = await fetchPublicItineraries();
    } catch (caught) {
      itineraries.value = [];
      error.value =
        caught instanceof Error ? caught.message : "Unable to load public itineraries.";
    } finally {
      isLoading.value = false;
    }
  }

  async function loadItineraryDetail(itineraryId: string): Promise<Itinerary | null> {
    if (!itineraryId) {
      selectedItinerary.value = null;
      error.value = "Missing itinerary ID.";
      return null;
    }

    isLoading.value = true;
    error.value = null;
    selectedItinerary.value = null;

    try {
      selectedItinerary.value = await fetchItineraryDetail(itineraryId);
      return selectedItinerary.value;
    } catch (caught) {
      error.value =
        caught instanceof Error ? caught.message : "Unable to load itinerary details.";
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  async function findExactPublicItinerary(
    criteria: ExactPublicItineraryCriteria,
  ): Promise<Itinerary | null> {
    isLoading.value = true;
    error.value = null;
    exactMatch.value = null;

    try {
      const candidates = await fetchPublicItineraries({
        cityId: criteria.destinationId,
        bookId: criteria.bookId,
        transportationMode: criteria.transportationMode,
      });
      exactMatch.value =
        candidates.find(
          (itinerary) =>
            itinerary.destinationId === criteria.destinationId &&
            itinerary.bookId === criteria.bookId &&
            itinerary.durationDays === criteria.durationDays &&
            itinerary.transportationMode === criteria.transportationMode,
        ) ?? null;
      return exactMatch.value;
    } catch (caught) {
      error.value =
        caught instanceof Error ? caught.message : "Unable to check public itineraries.";
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  function clearSelectedItinerary(): void {
    selectedItinerary.value = null;
    error.value = null;
  }

  function reset(): void {
    itineraries.value = [];
    selectedItinerary.value = null;
    exactMatch.value = null;
    isLoading.value = false;
    error.value = null;
  }

  return {
    itineraries,
    selectedItinerary,
    exactMatch,
    hasItineraries,
    isLoading,
    error,
    loadItineraries,
    loadItineraryDetail,
    findExactPublicItinerary,
    clearSelectedItinerary,
    reset,
  };
});

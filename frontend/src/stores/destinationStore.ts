import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { fetchDestinations } from "../services/destinationsApi";
import type { Destination } from "../types";

export const useDestinationStore = defineStore("destinations", () => {
  const destinations = ref<Destination[]>([]);
  const selectedDestinationId = ref<string | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const selectedDestination = computed(
    () =>
      destinations.value.find((destination) => destination.id === selectedDestinationId.value) ??
      null,
  );
  const hasDestinations = computed(() => destinations.value.length > 0);

  async function loadDestinations(): Promise<void> {
    isLoading.value = true;
    error.value = null;

    try {
      destinations.value = await fetchDestinations();
    } catch (caught) {
      error.value =
        caught instanceof Error ? caught.message : "Unable to load destinations.";
    } finally {
      isLoading.value = false;
    }
  }

  function selectDestination(destinationId: string): void {
    selectedDestinationId.value = destinationId;
  }

  function clearSelection(): void {
    selectedDestinationId.value = null;
  }

  function reset(): void {
    destinations.value = [];
    selectedDestinationId.value = null;
    isLoading.value = false;
    error.value = null;
  }

  return {
    destinations,
    selectedDestination,
    selectedDestinationId,
    hasDestinations,
    isLoading,
    error,
    loadDestinations,
    selectDestination,
    clearSelection,
    reset,
  };
});

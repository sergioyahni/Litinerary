<template>
  <section class="page-banner">
    <div class="container">
      <h1>Configure Your Litinerary</h1>
      <p>Set a short route length and transportation mode before generation.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div v-if="!destinationId || !bookId" class="placeholder-panel">
        <h2>Choose a destination and book first</h2>
        <p>The generator needs both selections before it can search for an exact repository match, adapt a partial match, or create a new mock itinerary.</p>
        <RouterLink class="button compact-button" :to="{ name: 'destinations' }">
          Start With Destination
        </RouterLink>
      </div>

      <form v-else class="config-panel" @submit.prevent="submit">
        <div>
          <p class="eyebrow">Selected route</p>
          <h2>{{ bookTitle }} in {{ destinationTitle }}</h2>
          <p>The backend will first check the public repository, then adapt or generate from local mock POIs.</p>
        </div>

        <label for="duration-days">Duration</label>
        <select
          id="duration-days"
          v-model.number="itineraryStore.durationDays"
          aria-describedby="duration-help"
        >
          <option :value="1">1 day</option>
          <option :value="2">2 days</option>
          <option :value="3">3 days</option>
        </select>
        <p id="duration-help" class="form-help">Routes can be one to three days.</p>

        <label for="transportation-mode">Transportation</label>
        <select
          id="transportation-mode"
          v-model="itineraryStore.transportationMode"
          aria-describedby="transportation-help"
        >
          <option value="walking">Walking</option>
          <option value="public_transport">Public transportation</option>
          <option value="car_taxi">Car or taxi</option>
        </select>
        <p id="transportation-help" class="form-help">Routing notes are mock guidance, not live travel directions.</p>

        <div v-if="itineraryStore.error" class="inline-error" role="alert">
          {{ itineraryStore.error }}
        </div>

        <RouterLink
          v-if="repositoryStore.exactMatch"
          class="button compact-button"
          :to="{
            name: 'itinerary-detail',
            params: { id: repositoryStore.exactMatch.id },
          }"
        >
          Open Existing Itinerary
        </RouterLink>
        <button
          v-else
          class="button compact-button"
          type="submit"
          :disabled="itineraryStore.isGenerating || repositoryStore.isCheckingExactMatch"
        >
          {{ generateButtonLabel }}
        </button>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/authStore";
import { useBookStore } from "../stores/bookStore";
import { useDestinationStore } from "../stores/destinationStore";
import { useItineraryRepositoryStore } from "../stores/itineraryRepositoryStore";
import { useItineraryStore } from "../stores/itineraryStore";

const route = useRoute();
const router = useRouter();
const bookStore = useBookStore();
const destinationStore = useDestinationStore();
const repositoryStore = useItineraryRepositoryStore();
const itineraryStore = useItineraryStore();
const authStore = useAuthStore();

const destinationId = computed(() => {
  const param = route.params.destinationId;
  return typeof param === "string" ? param : destinationStore.selectedDestinationId;
});

const bookId = computed(() => {
  const param = route.params.bookId;
  return typeof param === "string" ? param : bookStore.selectedBookId;
});

const destinationTitle = computed(
  () => destinationStore.selectedDestination?.name ?? destinationId.value ?? "Selected destination",
);

const bookTitle = computed(() => bookStore.selectedBook?.title ?? bookId.value ?? "Selected book");
const generateButtonLabel = computed(() => {
  if (repositoryStore.isCheckingExactMatch) {
    return "Checking Public Repository...";
  }
  if (itineraryStore.isGenerating) {
    return "Generating...";
  }
  return authStore.canGenerateItinerary ? "Generate Itinerary" : "Sign In to Generate";
});

onMounted(async () => {
  if (!destinationId.value || !bookId.value) {
    await router.replace({ name: "destinations" });
    return;
  }

  if (destinationStore.destinations.length === 0) {
    await destinationStore.loadDestinations();
  }

  if (!destinationStore.destinations.some((destination) => destination.id === destinationId.value)) {
    repositoryStore.clearExactMatch();
    return;
  }

  destinationStore.selectDestination(destinationId.value);

  if (
    bookStore.books.length === 0 ||
    !bookStore.books.some((book) => book.id === bookId.value)
  ) {
    await bookStore.loadBooks(destinationId.value);
  }

  if (bookStore.books.some((book) => book.id === bookId.value)) {
    bookStore.selectBook(bookId.value);
  } else {
    bookStore.clearBooks();
    repositoryStore.clearExactMatch();
    return;
  }

  await checkPublicRepository();
});

watch(
  [
    destinationId,
    bookId,
    () => itineraryStore.durationDays,
    () => itineraryStore.transportationMode,
  ],
  () => {
    void checkPublicRepository();
  },
);

async function checkPublicRepository(): Promise<void> {
  if (!destinationId.value || !bookId.value) {
    repositoryStore.clearExactMatch();
    return;
  }

  await repositoryStore.findExactPublicItinerary({
    destinationId: destinationId.value,
    bookId: bookId.value,
    durationDays: itineraryStore.durationDays,
    transportationMode: itineraryStore.transportationMode,
  });
}

async function submit(): Promise<void> {
  if (!destinationId.value || !bookId.value) {
    return;
  }

  if (repositoryStore.isCheckingExactMatch || repositoryStore.exactMatch) {
    return;
  }

  if (!authStore.canGenerateItinerary) {
    await authStore.login(route.fullPath);
    return;
  }

  const response = await itineraryStore.submitGeneration({
    destinationId: destinationId.value,
    bookId: bookId.value,
  });

  if (response) {
    await router.push({ name: "generated-itinerary" });
  }
}
</script>

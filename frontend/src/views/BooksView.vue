<template>
  <section class="page-banner">
    <div class="container">
      <h1>Choose a Book</h1>
      <p>{{ subtitle }}</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div v-if="!destinationId" class="placeholder-panel">
        <h2>Pick a destination first</h2>
        <p>Books are filtered by city so the generated itinerary can use relevant local stops.</p>
        <RouterLink class="button compact-button" :to="{ name: 'destinations' }">
          Choose Destination
        </RouterLink>
      </div>

      <template v-else>
        <form
          v-if="authStore.canUseExternalDiscovery"
          class="discovery-form"
          aria-label="Discover books beyond the public repository"
          @submit.prevent="discoverBooks"
        >
          <label for="book-discovery-query">Find another book</label>
          <div class="discovery-form-row">
            <input
              id="book-discovery-query"
              v-model="discoveryQuery"
              autocomplete="off"
              placeholder="Search by title or author"
              required
              type="search"
            />
            <button
              class="button compact-button"
              :disabled="bookStore.isLoading || !discoveryQuery.trim()"
              type="submit"
            >
              Search
            </button>
          </div>
        </form>

        <div v-if="bookStore.isLoading" class="placeholder-panel" aria-live="polite">
          <p class="loading-note">Loading books for {{ destinationLabel }}...</p>
        </div>

        <div v-else-if="bookStore.error" class="placeholder-panel error-panel" role="alert">
          <h2>Books could not load</h2>
          <p>{{ bookStore.error }}</p>
          <button class="button compact-button" type="button" @click="loadBooks">
            Try Loading Books Again
          </button>
        </div>

        <div v-else-if="bookStore.books.length === 0" class="placeholder-panel">
          <h2>No books for {{ destinationLabel }}</h2>
          <p>This mock destination has no book records yet. Choose another destination or add books to the mock catalog.</p>
        </div>

        <div v-else class="data-card-grid">
          <article v-for="book in bookStore.books" :key="book.id" class="data-card">
            <p class="eyebrow">{{ book.author }}</p>
            <h2>{{ book.title }}</h2>
            <p>{{ book.description }}</p>
            <div class="tag-row">
              <span v-for="theme in book.themes" :key="theme" class="tag">{{ theme }}</span>
            </div>
            <div v-if="book.affiliateLinks?.length" class="affiliate-link-list">
              <a
                v-for="link in book.affiliateLinks"
                :key="link.sourceUrl"
                :href="link.sourceUrl"
                rel="noopener noreferrer"
                target="_blank"
              >
                {{ link.title }}<span v-if="link.affiliate"> affiliate</span>
              </a>
            </div>
            <RouterLink
              class="button compact-button"
              :to="{
                name: 'itinerary-config-selection',
                params: { destinationId, bookId: book.id },
              }"
              @click="bookStore.selectBook(book.id)"
            >
              Configure {{ book.title }} Tour
            </RouterLink>
          </article>
        </div>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "../stores/authStore";
import { useBookStore } from "../stores/bookStore";
import { useDestinationStore } from "../stores/destinationStore";

const route = useRoute();
const authStore = useAuthStore();
const bookStore = useBookStore();
const destinationStore = useDestinationStore();
const discoveryQuery = ref("");

const destinationId = computed(() => {
  const param = route.params.destinationId;
  return typeof param === "string" ? param : destinationStore.selectedDestinationId;
});

const subtitle = computed(() =>
  destinationId.value
    ? `Select the book that will shape your itinerary for ${destinationLabel.value}.`
    : "Select a destination first so the book list can be filtered.",
);

const destinationLabel = computed(
  () => destinationStore.selectedDestination?.name ?? destinationId.value ?? "this destination",
);

function loadBooks(): void {
  if (destinationId.value) {
    destinationStore.selectDestination(destinationId.value);
    void bookStore.loadBooks(destinationId.value);
  }
}

function discoverBooks(): void {
  const query = discoveryQuery.value.trim();
  if (destinationId.value && query && authStore.canUseExternalDiscovery) {
    void bookStore.discoverMissingBooks(destinationId.value, query);
  }
}

onMounted(async () => {
  if (destinationStore.destinations.length === 0) {
    await destinationStore.loadDestinations();
  }
  loadBooks();
});
watch(destinationId, loadBooks);
</script>

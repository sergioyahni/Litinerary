<template>
  <section class="account-panel" aria-labelledby="account-panel-heading">
    <div>
      <p class="eyebrow">{{ authStore.isAuthEnabled ? "Litinerary account" : "Development account" }}</p>
      <h2 id="account-panel-heading">Save this itinerary</h2>
      <p>
        Anonymous planning still works. Sign in to save bookmarks and reviews to your account.
      </p>
    </div>

    <div v-if="userStore.error" class="inline-error" role="alert">
      {{ userStore.error }}
    </div>

    <button
      v-if="authStore.isAuthEnabled && !authStore.isAuthenticated"
      class="button compact-button"
      type="button"
      @click="authStore.login($route.fullPath)"
    >
      Sign In
    </button>

    <button
      v-else
      class="button compact-button"
      type="button"
      :disabled="userStore.isLoading"
      @click="userStore.toggleBookmark(itinerary)"
    >
      {{ userStore.isBookmarked(itinerary.id) ? "Remove Bookmark" : "Bookmark Itinerary" }}
    </button>

    <form v-if="!authStore.isAuthEnabled || authStore.isAuthenticated" class="review-form" @submit.prevent="submitReview">
      <label for="review-rating">Rating</label>
      <select id="review-rating" v-model.number="rating">
        <option :value="5">5 - Excellent</option>
        <option :value="4">4 - Good</option>
        <option :value="3">3 - Useful</option>
        <option :value="2">2 - Needs work</option>
        <option :value="1">1 - Not useful</option>
      </select>

      <label for="review-comment">Review note</label>
      <textarea
        id="review-comment"
        v-model="comment"
        rows="3"
        placeholder="What worked or should be improved?"
      />

      <button class="button compact-button" type="submit" :disabled="userStore.isLoading">
        Save Review
      </button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useAuthStore } from "../../stores/authStore";
import { useUserStore } from "../../stores/userStore";
import type { Itinerary } from "../../types";

const props = defineProps<{
  itinerary: Itinerary;
}>();

const authStore = useAuthStore();
const userStore = useUserStore();
const rating = ref(5);
const comment = ref("");

onMounted(() => {
  if (!authStore.isAuthEnabled || authStore.isAuthenticated) {
    void userStore.loadBookmarks();
  }
});

async function submitReview(): Promise<void> {
  const saved = await userStore.submitReview(props.itinerary.id, rating.value, comment.value);
  if (saved) {
    comment.value = "";
  }
}
</script>

<template>
  <section class="page-banner">
    <div class="container">
      <h1>Development Profile</h1>
      <p>Use a temporary Phase 2 user record to try preferences, bookmarks, and reviews.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div class="config-panel">
        <div>
          <p class="eyebrow">Not production authentication</p>
          <h2>{{ userStore.profile?.displayName ?? "Development Reader" }}</h2>
          <p>User ID: {{ userStore.userId }}</p>
        </div>

        <div v-if="userStore.error" class="inline-error" role="alert">
          {{ userStore.error }}
        </div>

        <button class="button compact-button" type="button" @click="userStore.ensureDevelopmentUser">
          Create or Load Development User
        </button>

        <form class="review-form" @submit.prevent="savePreferences">
          <label for="preferred-pace">Preferred pace</label>
          <select id="preferred-pace" v-model="preferredPace">
            <option value="slow">Slow</option>
            <option value="balanced">Balanced</option>
            <option value="packed">Packed</option>
          </select>

          <label for="preferred-theme">Preferred theme</label>
          <input id="preferred-theme" v-model="preferredTheme" type="text" />

          <button class="button compact-button" type="submit" :disabled="userStore.isLoading">
            Save Preferences
          </button>
        </form>

        <div class="source-note-panel">
          <h2>Saved Preferences</h2>
          <p v-if="!userStore.profile?.preferences.length">No preferences saved yet.</p>
          <ul v-else>
            <li v-for="preference in userStore.profile.preferences" :key="preference.id">
              {{ preference.key }}: {{ JSON.stringify(preference.value) }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useUserStore } from "../stores/userStore";

const userStore = useUserStore();
const preferredPace = ref("balanced");
const preferredTheme = ref("classic literature");

onMounted(() => {
  void userStore.loadProfile();
});

function savePreferences(): void {
  void userStore.savePreferences({
    pace: preferredPace.value,
    theme: preferredTheme.value,
  });
}
</script>

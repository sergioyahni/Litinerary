<template>
  <section class="page-banner">
    <div class="container">
      <h1>Signing In</h1>
      <p v-if="authStore.error" role="alert">{{ authStore.error }}</p>
      <p v-else>Finishing your secure Litinerary session.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div class="placeholder-panel">
        <h2>{{ authStore.error ? "Sign-in could not finish" : "One moment" }}</h2>
        <p v-if="authStore.error">
          The session was not established. Please start sign-in again.
        </p>
        <p v-else aria-live="polite">Checking your session...</p>
        <button
          v-if="authStore.error"
          class="button compact-button"
          type="button"
          @click="authStore.login('/')"
        >
          Sign In
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/authStore";

const authStore = useAuthStore();
const router = useRouter();

onMounted(async () => {
  if (authStore.isAuthenticated) {
    await router.replace({ name: "user-profile" });
    return;
  }
  await authStore.restoreSession();
  if (authStore.isAuthenticated) {
    await router.replace({ name: "user-profile" });
  }
});
</script>

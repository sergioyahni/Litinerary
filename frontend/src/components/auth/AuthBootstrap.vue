<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useAuth0 } from "@auth0/auth0-vue";
import { setAuth0Client, usesAuth0 } from "../../services/authService";
import { useAuthStore } from "../../stores/authStore";

const authStore = useAuthStore();

if (usesAuth0() && authStore.isAuth0Configured) {
  const auth0 = useAuth0();
  setAuth0Client(auth0);

  onMounted(() => {
    void authStore.restoreSession();
  });

  watch(
    () => auth0.isAuthenticated.value,
    (isAuthenticated) => {
      if (isAuthenticated) {
        void authStore.hydrateAuthenticatedUser();
      }
    },
  );
} else {
  setAuth0Client(null);
}
</script>

<template></template>

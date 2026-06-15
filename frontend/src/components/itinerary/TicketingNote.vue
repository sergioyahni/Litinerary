<template>
  <p class="ticketing-note">
    <strong>{{ label }}</strong>
    <span>{{ note || "No ticketing note available yet." }}</span>
    <a v-if="url" :href="url" rel="noopener noreferrer" target="_blank">
      View logistics link
    </a>
  </p>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    note?: string;
    label?: string;
    url?: string | null;
  }>(),
  {
    label: "Ticketing",
  },
);
</script>

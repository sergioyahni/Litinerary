<template>
  <nav class="main-navigation" aria-label="Main navigation">
    <RouterLink
      v-for="item in navItems"
      :key="item.name"
      class="nav-link"
      :to="{ name: item.name }"
      @click="$emit('navigate')"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
defineEmits<{
  navigate: [];
}>();

const navItems = [
  { label: "Home", name: "home" },
  { label: "Destinations", name: "destinations" },
  { label: "Books by City", name: "books" },
  { label: "Configure Tour", name: "itinerary-config" },
  { label: "Public Repository", name: "itinerary-repository" },
  { label: "Profile", name: "user-profile" },
  { label: "Bookmarks", name: "user-bookmarks" },
];
</script>

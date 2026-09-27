<template>
  <nav class="main-navigation" aria-label="Main navigation">
    <section
      v-for="section in navSections"
      :key="section.id"
      class="nav-accordion-section"
    >
      <button
        class="nav-accordion-trigger"
        type="button"
        :aria-expanded="openSections[section.id]"
        :aria-controls="`${section.id}-panel`"
        @click="toggleSection(section.id)"
      >
        <span>{{ section.label }}</span>
        <span class="nav-accordion-icon" aria-hidden="true"></span>
      </button>
      <div
        v-show="openSections[section.id]"
        :id="`${section.id}-panel`"
        class="nav-accordion-panel"
      >
        <RouterLink
          v-for="item in section.items"
          :key="item.name"
          class="nav-link"
          :to="{ name: item.name }"
          @click="$emit('navigate')"
        >
          {{ item.label }}
        </RouterLink>
      </div>
    </section>
  </nav>
</template>

<script setup lang="ts">
import { reactive } from "vue";

defineEmits<{
  navigate: [];
}>();

interface NavItem {
  label: string;
  name: string;
}

interface NavSection {
  id: string;
  label: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    id: "nav-discover",
    label: "Discover",
    items: [
      { label: "Home", name: "home" },
      { label: "Destinations", name: "destinations" },
      { label: "Books by City", name: "books" },
    ],
  },
  {
    id: "nav-plan",
    label: "Plan",
    items: [
      { label: "Configure Tour", name: "itinerary-config" },
      { label: "Public Repository", name: "itinerary-repository" },
    ],
  },
  {
    id: "nav-account",
    label: "Account",
    items: [
      { label: "Profile", name: "user-profile" },
      { label: "Bookmarks", name: "user-bookmarks" },
    ],
  },
];

const openSections = reactive<Record<string, boolean>>(
  Object.fromEntries(navSections.map((section) => [section.id, true])),
);

function toggleSection(sectionId: string): void {
  openSections[sectionId] = !openSections[sectionId];
}
</script>

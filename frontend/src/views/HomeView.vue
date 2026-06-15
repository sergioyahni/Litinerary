<template>
  <section class="hero-banner">
    <div class="container hero-grid">
      <div class="hero-copy">
        <p class="eyebrow">Phase 1 literary travel MVP</p>
        <h1>Plan a Book-Led City Walk</h1>
        <p>
          Choose a destination, pick a book, and generate a deterministic mock
          itinerary with mapped stops and readable day-by-day notes.
        </p>

        <div class="hero-search-form" aria-labelledby="mvp-flow-heading">
          <h2 id="mvp-flow-heading">MVP planning flow</h2>
          <ol class="flow-list">
            <li>Select a supported destination.</li>
            <li>Choose a book connected to that place.</li>
            <li>Set duration and transportation mode.</li>
            <li>Generate an itinerary, then review the map and stop list.</li>
          </ol>
          <RouterLink class="button button-hero" :to="{ name: 'destinations' }">
            Start With Destinations
          </RouterLink>
        </div>
      </div>

      <div class="hero-art">
        <img :src="heroImage" alt="Literary walking tour illustration" />
      </div>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div class="section-intro">
        <img :src="sectionLogo" alt="" />
        <h2>Sample Literary Routes</h2>
        <p>Preview the kind of book-and-place pairings available in the mock data.</p>
      </div>

      <div class="route-card-grid">
        <article v-for="route in previewRoutes" :key="route.title" class="route-card">
          <img :src="route.image" :alt="route.alt" />
          <div>
            <h3>{{ route.title }}</h3>
            <p>{{ route.description }}</p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import heroImage from "../assets/template/home/hero-img.png";
import londonImage from "../assets/template/home/london.jpg";
import parisImage from "../assets/template/home/paris.jpg";
import samarkandImage from "../assets/template/home/samarkand.jpg";
import sectionLogo from "../assets/template/logo_img.png";

const previewRoutes = [
  {
    title: "London with Oliver Twist",
    description: "A route through markets, alleys, and river views shaped by Dickensian London.",
    image: londonImage,
    alt: "London walking tour",
  },
  {
    title: "Paris with Robert Langdon",
    description: "A city route for readers who like symbols, museums, and dramatic reveals.",
    image: parisImage,
    alt: "Paris walking tour",
  },
  {
    title: "Samarkand with Omar Khayyam",
    description: "A poetic journey through blue tiles, old roads, and layered memory.",
    image: samarkandImage,
    alt: "Samarkand walking tour",
  },
];
</script>

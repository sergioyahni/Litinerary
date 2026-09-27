<template>
  <section class="hero-banner">
    <div class="container hero-grid">
      <div class="hero-copy">
        <p class="eyebrow">literary travel</p>
        <h1>Plan Your Book-Led City Visit</h1>
        <p>
          Choose a destination, pick a book, and generate an itinerary with mapped stops and day-by-day notes.
        </p>

        <div class="hero-search-form" aria-labelledby="mvp-flow-heading">
          <h2 id="mvp-flow-heading">How to Plan Your Literary Walk?</h2>
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
</template>

<script setup lang="ts">
import heroImage from "../assets/template/home/hero-img.png";
</script>

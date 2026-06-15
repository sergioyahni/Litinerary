<template>
  <footer class="footer-area">
    <div class="container footer-grid">
      <section class="single-footer-widget">
        <h2>About Litinerary</h2>
        <p>
          A literary travel companion for mapping books, authors, characters, and
          scenes to real-world journeys.
        </p>
      </section>

      <section class="single-footer-widget">
        <h2>Explore</h2>
        <ul>
          <li><RouterLink :to="{ name: 'home' }">Home</RouterLink></li>
          <li><RouterLink :to="{ name: 'destinations' }">Destinations</RouterLink></li>
          <li><RouterLink :to="{ name: 'books' }">Books</RouterLink></li>
          <li><RouterLink :to="{ name: 'itinerary-repository' }">Litineraries</RouterLink></li>
        </ul>
      </section>

      <section class="single-footer-widget">
        <h2>Plan</h2>
        <ul>
          <li><RouterLink :to="{ name: 'itinerary-config' }">Configure a Tour</RouterLink></li>
          <li><RouterLink :to="{ name: 'generated-itinerary' }">Generated Itinerary</RouterLink></li>
          <li><RouterLink :to="{ name: 'itinerary-detail', params: { id: 'sample' } }">Itinerary Detail</RouterLink></li>
        </ul>
      </section>

      <section class="single-footer-widget">
        <h2>Newsletter</h2>
        <p>Follow future literary routes, city guides, and new template updates.</p>
        <form class="footer-form" @submit.prevent>
          <label class="visually-hidden" for="newsletter-email">Email address</label>
          <input id="newsletter-email" type="email" placeholder="Email Address" />
          <button class="footer-submit" type="submit" aria-label="Subscribe">→</button>
        </form>
      </section>
    </div>

    <div class="container footer-bottom">
      <p>Copyright © {{ year }} Litinerary. Template visual direction preserved for app development.</p>
    </div>
  </footer>
</template>

<script setup lang="ts">
const year = new Date().getFullYear();
</script>

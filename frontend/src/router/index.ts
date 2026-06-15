import { createRouter, createWebHistory } from "vue-router";
import BooksView from "../views/BooksView.vue";
import DestinationsView from "../views/DestinationsView.vue";
import GeneratedItineraryView from "../views/GeneratedItineraryView.vue";
import HomeView from "../views/HomeView.vue";
import ItineraryConfigView from "../views/ItineraryConfigView.vue";
import ItineraryDetailView from "../views/ItineraryDetailView.vue";
import ItineraryRepositoryView from "../views/ItineraryRepositoryView.vue";
import SubscriberChatView from "../views/SubscriberChatView.vue";
import UserBookmarksView from "../views/UserBookmarksView.vue";
import UserProfileView from "../views/UserProfileView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/destinations",
      name: "destinations",
      component: DestinationsView,
    },
    {
      path: "/books",
      name: "books",
      component: BooksView,
    },
    {
      path: "/destinations/:destinationId/books",
      name: "destination-books",
      component: BooksView,
    },
    {
      path: "/itinerary/configure",
      name: "itinerary-config",
      component: ItineraryConfigView,
    },
    {
      path: "/itinerary/configure/:destinationId/:bookId",
      name: "itinerary-config-selection",
      component: ItineraryConfigView,
    },
    {
      path: "/itinerary/generated",
      name: "generated-itinerary",
      component: GeneratedItineraryView,
    },
    {
      path: "/itineraries",
      name: "itinerary-repository",
      component: ItineraryRepositoryView,
    },
    {
      path: "/itineraries/:id",
      name: "itinerary-detail",
      component: ItineraryDetailView,
    },
    {
      path: "/account",
      name: "user-profile",
      component: UserProfileView,
    },
    {
      path: "/account/bookmarks",
      name: "user-bookmarks",
      component: UserBookmarksView,
    },
    {
      path: "/subscriber/chat",
      name: "subscriber-chat",
      component: SubscriberChatView,
    },
  ],
});

export default router;

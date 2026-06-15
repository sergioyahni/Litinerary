import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App.vue";
import router from "../router";
import { fetchBooksByDestination } from "../services/booksApi";
import { fetchDestinations } from "../services/destinationsApi";
import {
  fetchItineraryDetail,
  fetchPublicItineraries,
  generateItinerary,
} from "../services/itinerariesApi";
import {
  bookmarkItinerary,
  createUser,
  fetchUser,
  fetchUserBookmarks,
  fetchUserReviews,
  saveUserPreference,
  saveUserReview,
} from "../services/usersApi";
import { useUserStore } from "../stores/userStore";
import { bookFixture, destinationFixture, itineraryFixture } from "./fixtures";

let pinia: ReturnType<typeof createPinia>;

vi.mock("leaflet", () => {
  const chainableLayer = {
    addTo: vi.fn().mockReturnThis(),
    bindPopup: vi.fn().mockReturnThis(),
  };
  const map = {
    fitBounds: vi.fn(),
    invalidateSize: vi.fn(),
    remove: vi.fn(),
  };
  const layerGroup = {
    addTo: vi.fn().mockReturnThis(),
    clearLayers: vi.fn(),
  };

  return {
    default: {
      divIcon: vi.fn((options) => options),
      latLngBounds: vi.fn((points) => points),
      layerGroup: vi.fn(() => layerGroup),
      map: vi.fn(() => map),
      marker: vi.fn(() => chainableLayer),
      polyline: vi.fn(() => chainableLayer),
      tileLayer: vi.fn(() => chainableLayer),
    },
  };
});

vi.mock("../services/destinationsApi", () => ({
  fetchDestinations: vi.fn(),
}));

vi.mock("../services/booksApi", () => ({
  fetchBooksByDestination: vi.fn(),
}));

vi.mock("../services/itinerariesApi", () => ({
  adaptItinerary: vi.fn(),
  fetchItineraryDetail: vi.fn(),
  fetchPublicItineraries: vi.fn(),
  generateItinerary: vi.fn(),
}));

vi.mock("../services/usersApi", () => ({
  bookmarkItinerary: vi.fn(),
  createUser: vi.fn(),
  fetchUser: vi.fn(),
  fetchUserBookmarks: vi.fn(),
  fetchUserReviews: vi.fn(),
  removeItineraryBookmark: vi.fn(),
  saveUserPreference: vi.fn(),
  saveUserReview: vi.fn(),
}));

const userProfile = {
  id: "dev-reader",
  displayName: "Development Reader",
  createdAt: "2026-06-10T00:00:00.000Z",
  preferences: [],
  reviews: [],
};

const review = {
  id: "review-smoke",
  userId: "dev-reader",
  itineraryId: itineraryFixture.id,
  rating: 5,
  comment: "Useful smoke review",
  createdAt: "2026-06-10T00:00:00.000Z",
};

async function navigateTo(name: string, params?: Record<string, string>): Promise<void> {
  await router.push({ name, params });
  await flushPromises();
}

describe("MVP and Phase 2 happy-path smoke flow", () => {
  beforeEach(async () => {
    vi.mocked(fetchDestinations).mockResolvedValue([destinationFixture]);
    vi.mocked(fetchBooksByDestination).mockResolvedValue([bookFixture]);
    vi.mocked(generateItinerary).mockResolvedValue({
      itinerary: itineraryFixture,
      matchedExisting: true,
      sourceItineraryId: itineraryFixture.id,
      message: "Matched an existing public itinerary.",
    });
    vi.mocked(fetchPublicItineraries).mockResolvedValue([itineraryFixture]);
    vi.mocked(fetchItineraryDetail).mockResolvedValue(itineraryFixture);
    vi.mocked(fetchUser).mockResolvedValue(userProfile);
    vi.mocked(createUser).mockResolvedValue(userProfile);
    vi.mocked(fetchUserBookmarks).mockResolvedValue([]);
    vi.mocked(bookmarkItinerary).mockResolvedValue({
      userId: "dev-reader",
      itineraries: [itineraryFixture],
    });
    vi.mocked(saveUserPreference).mockResolvedValue({
      id: "preference-smoke",
      userId: "dev-reader",
      key: "travel",
      value: { pace: "slow", interests: ["markets"] },
      createdAt: "2026-06-10T00:00:00.000Z",
    });
    vi.mocked(saveUserReview).mockResolvedValue(review);
    vi.mocked(fetchUserReviews).mockResolvedValue([review]);

    pinia = createPinia();
    setActivePinia(pinia);
    await router.push("/");
    await router.isReady();
  });

  it("covers planning, generated itinerary, repository detail, and account actions", async () => {
    const wrapper = mount(App, {
      global: {
        plugins: [pinia, router],
      },
    });

    expect(wrapper.text()).toContain("Plan a Book-Led City Walk");

    await navigateTo("destinations");
    expect(fetchDestinations).toHaveBeenCalled();
    expect(wrapper.text()).toContain("Choose a Destination");
    expect(wrapper.text()).toContain("London");

    await navigateTo("destination-books", { destinationId: "london" });
    expect(fetchBooksByDestination).toHaveBeenCalledWith("london");
    expect(wrapper.text()).toContain("Choose a Book");
    expect(wrapper.text()).toContain("Oliver Twist");

    await navigateTo("itinerary-config-selection", {
      destinationId: "london",
      bookId: "oliver-twist",
    });
    expect(wrapper.text()).toContain("Configure Your Litinerary");

    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(generateItinerary).toHaveBeenCalledWith({
      destinationId: "london",
      bookId: "oliver-twist",
      durationDays: 1,
      transportationMode: "walking",
    });
    expect(wrapper.text()).toContain("Your Generated Litinerary");
    expect(wrapper.text()).toContain("Smithfield Market");
    expect(wrapper.text()).toContain("Mapped stop list");

    const bookmarkButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Bookmark Itinerary"));
    expect(bookmarkButton).toBeTruthy();
    await bookmarkButton?.trigger("click");
    await flushPromises();
    expect(bookmarkItinerary).toHaveBeenCalledWith("dev-reader", itineraryFixture.id);
    expect(wrapper.text()).toContain("Remove Bookmark");

    await wrapper.get("textarea").setValue("Useful smoke review");
    await wrapper.get("form.review-form").trigger("submit");
    await flushPromises();
    expect(saveUserReview).toHaveBeenCalledWith("dev-reader", {
      itineraryId: itineraryFixture.id,
      rating: 5,
      comment: "Useful smoke review",
    });

    const userStore = useUserStore();
    await userStore.savePreferences({ pace: "slow", interests: ["markets"] });
    expect(saveUserPreference).toHaveBeenCalledWith("dev-reader", {
      key: "travel",
      value: { pace: "slow", interests: ["markets"] },
    });

    await navigateTo("itinerary-repository");
    expect(fetchPublicItineraries).toHaveBeenCalled();
    expect(wrapper.text()).toContain("Public Litineraries");
    expect(wrapper.text()).toContain("Oliver Twist in London");

    await navigateTo("itinerary-detail", { id: itineraryFixture.id });
    expect(fetchItineraryDetail).toHaveBeenCalledWith(itineraryFixture.id);
    expect(wrapper.text()).toContain("Itinerary Detail");
    expect(wrapper.text()).toContain("Smithfield Market");
    expect(wrapper.text()).toContain("Mapped stop list");
  });
});

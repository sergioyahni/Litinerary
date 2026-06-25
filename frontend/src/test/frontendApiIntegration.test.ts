import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App.vue";
import router from "../router";
import { fetchBooksByDestination } from "../services/booksApi";
import { fetchDestinations } from "../services/destinationsApi";
import {
  fetchItineraryDetail,
  fetchItineraryNarration,
  fetchPublicItineraries,
  generateItinerary,
  generateItineraryNarration,
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
import {
  destinationFixture,
  sherlockBookFixture,
  sherlockGenerationResponseFixture,
  sherlockItineraryFixture,
} from "./fixtures";

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
  fetchItineraryNarration: vi.fn(),
  fetchPublicItineraries: vi.fn(),
  generateItinerary: vi.fn(),
  generateItineraryNarration: vi.fn(),
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

const safeNarration = {
  itineraryId: sherlockItineraryFixture.id,
  script: {
    itineraryId: sherlockItineraryFixture.id,
    title: "Narration for Sherlock Holmes in London",
    text: "Begin at Baker Street and keep all routing assumptions mock-only.",
    estimatedDurationSeconds: 45,
    providerName: "mock_tts",
    providerType: "tts",
    providerVersion: "local-mock",
    provenanceMetadata: {
      provider_name: "mock_tts",
      provider_type: "tts",
      warnings: ["No external TTS provider call was made."],
    },
  },
  audio: {
    available: false,
    url: null,
    format: null,
    durationSeconds: null,
    providerName: "mock_tts",
    providerType: "tts",
    providerVersion: "local-mock",
    placeholder: true,
    warnings: ["No external TTS provider call was made."],
  },
  format: "text_only" as const,
};

async function navigateTo(name: string, params?: Record<string, string>): Promise<void> {
  await router.push({ name, params });
  await flushPromises();
}

function mountApp() {
  return mount(App, {
    global: {
      plugins: [createPinia(), router],
    },
  });
}

function expectSafeUiText(text: string): void {
  expect(text).not.toContain("rawProviderPayload");
  expect(text).not.toContain("raw_provider_payload");
  expect(text).not.toContain("Authorization");
  expect(text).not.toMatch(/sk-[A-Za-z0-9_-]{20,}/);
  expect(text).not.toMatch(/Bearer\s+[A-Za-z0-9._-]{20,}/i);
}

describe("Batch 3 frontend/API integration flow", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    vi.mocked(fetchDestinations).mockResolvedValue([destinationFixture]);
    vi.mocked(fetchBooksByDestination).mockResolvedValue([sherlockBookFixture]);
    vi.mocked(generateItinerary).mockResolvedValue(sherlockGenerationResponseFixture);
    vi.mocked(fetchPublicItineraries).mockResolvedValue([sherlockItineraryFixture]);
    vi.mocked(fetchItineraryDetail).mockResolvedValue(sherlockItineraryFixture);
    vi.mocked(fetchItineraryNarration).mockResolvedValue(safeNarration);
    vi.mocked(generateItineraryNarration).mockResolvedValue(safeNarration);
    vi.mocked(fetchUser).mockResolvedValue(userProfile);
    vi.mocked(createUser).mockResolvedValue(userProfile);
    vi.mocked(fetchUserBookmarks).mockResolvedValue([]);
    vi.mocked(bookmarkItinerary).mockResolvedValue({
      userId: "dev-reader",
      itineraries: [sherlockItineraryFixture],
    });
    vi.mocked(saveUserPreference).mockResolvedValue({
      id: "preference-integration",
      userId: "dev-reader",
      key: "travel",
      value: { pace: "slow" },
      createdAt: "2026-06-10T00:00:00.000Z",
    });
    vi.mocked(saveUserReview).mockResolvedValue({
      id: "review-integration",
      userId: "dev-reader",
      itineraryId: sherlockItineraryFixture.id,
      rating: 5,
      comment: "Baker Street worked well.",
      createdAt: "2026-06-10T00:00:00.000Z",
    });
    vi.mocked(fetchUserReviews).mockResolvedValue([]);
    await router.push("/");
    await router.isReady();
  });

  it("generates the London Sherlock itinerary and renders Baker Street safely", async () => {
    const wrapper = mountApp();

    await navigateTo("itinerary-config-selection", {
      destinationId: "london",
      bookId: "sherlock-holmes",
    });

    expect(wrapper.text()).toContain("Configure Your Litinerary");
    expect(wrapper.text()).toContain("The Adventures of Sherlock Holmes");
    await wrapper.get("form.config-panel").trigger("submit");
    await flushPromises();

    expect(generateItinerary).toHaveBeenCalledWith({
      destinationId: "london",
      bookId: "sherlock-holmes",
      durationDays: 1,
      transportationMode: "walking",
    });
    expect(wrapper.text()).toContain("Your Generated Litinerary");
    expect(wrapper.text()).toContain("The Adventures of Sherlock Holmes in London");
    expect(wrapper.text()).toContain("Baker Street");
    expect(wrapper.text()).toContain("The symbolic center of Holmes' London.");
    expect(wrapper.text()).toContain("verify real distances later");
    expect(wrapper.text()).toContain("Mapped stop list");
    expectSafeUiText(wrapper.text());
  });

  it("renders seeded repository list, detail, loading, and empty states", async () => {
    let resolveList: (value: typeof sherlockItineraryFixture[]) => void;
    vi.mocked(fetchPublicItineraries).mockReturnValue(
      new Promise((resolve) => {
        resolveList = resolve;
      }),
    );
    const wrapper = mountApp();

    await navigateTo("itinerary-repository");
    expect(wrapper.text()).toContain("Loading public itineraries");
    resolveList!([sherlockItineraryFixture]);
    await flushPromises();

    expect(wrapper.text()).toContain("Public Litineraries");
    expect(wrapper.text()).toContain("The Adventures of Sherlock Holmes in London");
    expect(wrapper.text()).toContain("deterministic mock itinerary candidate");
    expectSafeUiText(wrapper.text());

    await navigateTo("itinerary-detail", { id: sherlockItineraryFixture.id });
    expect(fetchItineraryDetail).toHaveBeenCalledWith(sherlockItineraryFixture.id);
    expect(wrapper.text()).toContain("Itinerary Detail");
    expect(wrapper.text()).toContain("Baker Street");
    expect(wrapper.text()).toContain("Text Itinerary");
    expectSafeUiText(wrapper.text());

    vi.mocked(fetchPublicItineraries).mockResolvedValue([]);
    await navigateTo("itinerary-repository");
    await flushPromises();
    expect(wrapper.text()).toContain("No public itineraries yet");
  });

  it("shows controlled generation errors without leaking raw provider details", async () => {
    vi.mocked(generateItinerary).mockRejectedValueOnce(
      new Error("Book 'les-miserables' is not available for destination 'london'"),
    );
    const wrapper = mountApp();

    await navigateTo("itinerary-config-selection", {
      destinationId: "london",
      bookId: "sherlock-holmes",
    });
    await wrapper.get("form.config-panel").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("Book 'les-miserables' is not available");
    expect(wrapper.text()).not.toContain("Generating...");
    expect(wrapper.text()).not.toContain("Your Generated Litinerary");
    expectSafeUiText(wrapper.text());

    vi.mocked(generateItinerary).mockRejectedValueOnce(
      new Error("Provider unavailable; use mock/offline mode."),
    );
    await wrapper.get("form.config-panel").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("Provider unavailable");
    expectSafeUiText(wrapper.text());
  });

  it("shows repository and detail API errors without infinite loading or stack traces", async () => {
    vi.mocked(fetchPublicItineraries).mockRejectedValue(new Error("Repository unavailable"));
    const wrapper = mountApp();

    await navigateTo("itinerary-repository");
    await flushPromises();
    expect(wrapper.text()).toContain("Repository could not load");
    expect(wrapper.text()).toContain("Repository unavailable");
    expect(wrapper.text()).not.toContain("Loading public itineraries");
    expect(wrapper.text()).not.toContain("at Object.");
    expectSafeUiText(wrapper.text());

    vi.mocked(fetchItineraryDetail).mockRejectedValue(new Error("Itinerary not found"));
    await navigateTo("itinerary-detail", { id: "missing-itinerary" });
    await flushPromises();
    expect(wrapper.text()).toContain("Itinerary could not load");
    expect(wrapper.text()).toContain("Itinerary not found");
    expect(wrapper.text()).not.toContain("Loading itinerary");
    expect(wrapper.text()).not.toContain("at Object.");
    expectSafeUiText(wrapper.text());
  });
});

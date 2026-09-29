import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount, RouterLinkStub } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { bookFixture, destinationFixture, itineraryFixture } from "../test/fixtures";
import ItineraryConfigView from "./ItineraryConfigView.vue";

const mocks = vi.hoisted(() => ({
  auth: {
    canGenerateItinerary: false,
    canUseExternalDiscovery: false,
    login: vi.fn(),
  },
  fetchBooksByDestination: vi.fn(),
  fetchDestinations: vi.fn(),
  fetchItineraryDetail: vi.fn(),
  fetchPublicItineraries: vi.fn(),
  generateItinerary: vi.fn(),
  route: {
    fullPath: "/itinerary/configure/london/oliver-twist",
    params: { destinationId: "london", bookId: "oliver-twist" },
  },
  router: { push: vi.fn(), replace: vi.fn() },
}));

vi.mock("../stores/authStore", () => ({
  useAuthStore: () => mocks.auth,
}));

vi.mock("../services/booksApi", () => ({
  discoverBooks: vi.fn(),
  fetchBooksByDestination: mocks.fetchBooksByDestination,
}));

vi.mock("../services/destinationsApi", () => ({
  discoverDestinations: vi.fn(),
  fetchDestinations: mocks.fetchDestinations,
}));

vi.mock("../services/itinerariesApi", () => ({
  fetchItineraryDetail: mocks.fetchItineraryDetail,
  fetchPublicItineraries: mocks.fetchPublicItineraries,
  generateItinerary: mocks.generateItinerary,
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRoute: () => mocks.route,
    useRouter: () => mocks.router,
  };
});

function mountConfiguration() {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(ItineraryConfigView, {
    global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } },
  });
}

describe("public itinerary planner handoff", () => {
  beforeEach(() => {
    mocks.auth.canGenerateItinerary = false;
    mocks.auth.login.mockReset();
    mocks.fetchBooksByDestination.mockReset();
    mocks.fetchDestinations.mockReset();
    mocks.fetchItineraryDetail.mockReset();
    mocks.fetchPublicItineraries.mockReset();
    mocks.generateItinerary.mockReset();
    mocks.router.push.mockReset();
    mocks.router.replace.mockReset();
    mocks.fetchBooksByDestination.mockResolvedValue([bookFixture]);
    mocks.fetchDestinations.mockResolvedValue([destinationFixture]);
  });

  it("offers an anonymous exact match through the canonical detail route", async () => {
    mocks.fetchPublicItineraries.mockResolvedValue([itineraryFixture]);
    const wrapper = mountConfiguration();

    await flushPromises();

    expect(mocks.fetchPublicItineraries).toHaveBeenCalledWith({
      cityId: "london",
      bookId: "oliver-twist",
      transportationMode: "walking",
    });
    const openLink = wrapper
      .findAllComponents(RouterLinkStub)
      .find((link) => link.text().includes("Open Existing Itinerary"));
    expect(openLink?.props("to")).toEqual({
      name: "itinerary-detail",
      params: { id: "it-london-oliver-twist-1-walking" },
    });
    expect(wrapper.find("form.discovery-form").exists()).toBe(false);
    expect(wrapper.find('form.config-panel button[type="submit"]').exists()).toBe(false);
    expect(mocks.generateItinerary).not.toHaveBeenCalled();
  });

  it("keeps an anonymous no-match configuration sign-in gated", async () => {
    mocks.fetchPublicItineraries.mockResolvedValue([]);
    const wrapper = mountConfiguration();
    await flushPromises();

    const submitButton = wrapper.get('form.config-panel button[type="submit"]');
    expect(submitButton.text()).toBe("Sign In to Generate");
    expect(wrapper.text()).not.toContain("Open Existing Itinerary");
    expect(wrapper.find("form.discovery-form").exists()).toBe(false);

    await wrapper.get("form.config-panel").trigger("submit");
    await flushPromises();

    expect(mocks.auth.login).toHaveBeenCalledWith(mocks.route.fullPath);
    expect(mocks.generateItinerary).not.toHaveBeenCalled();
  });

  it("preserves authenticated generation for a no-match configuration", async () => {
    mocks.auth.canGenerateItinerary = true;
    mocks.fetchPublicItineraries.mockResolvedValue([]);
    mocks.generateItinerary.mockResolvedValue({
      itinerary: itineraryFixture,
      matchedExisting: false,
      sourceItineraryId: null,
      message: "Generated itinerary.",
    });
    const wrapper = mountConfiguration();
    await flushPromises();

    expect(wrapper.get('form.config-panel button[type="submit"]').text()).toBe(
      "Generate Itinerary",
    );
    await wrapper.get("form.config-panel").trigger("submit");
    await flushPromises();

    expect(mocks.generateItinerary).toHaveBeenCalledWith({
      destinationId: "london",
      bookId: "oliver-twist",
      durationDays: 1,
      transportationMode: "walking",
    });
    expect(mocks.router.push).toHaveBeenCalledWith({ name: "generated-itinerary" });
  });
});

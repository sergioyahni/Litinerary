import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount, RouterLinkStub } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { bookFixture, destinationFixture } from "../test/fixtures";
import { useBookStore } from "../stores/bookStore";
import { useDestinationStore } from "../stores/destinationStore";
import BooksView from "./BooksView.vue";
import DestinationsView from "./DestinationsView.vue";

const mocks = vi.hoisted(() => ({
  auth: { canUseExternalDiscovery: false },
  routeParams: { destinationId: "london" },
  discoverBooks: vi.fn(),
  discoverDestinations: vi.fn(),
  fetchBooksByDestination: vi.fn(),
  fetchDestinations: vi.fn(),
}));

vi.mock("../stores/authStore", () => ({
  useAuthStore: () => mocks.auth,
}));

vi.mock("../services/booksApi", () => ({
  discoverBooks: mocks.discoverBooks,
  fetchBooksByDestination: mocks.fetchBooksByDestination,
}));

vi.mock("../services/destinationsApi", () => ({
  discoverDestinations: mocks.discoverDestinations,
  fetchDestinations: mocks.fetchDestinations,
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRoute: () => ({ params: mocks.routeParams }),
  };
});

const externalBook = {
  ...bookFixture,
  id: "external-london-bleak-house",
  title: "Bleak House",
  description: "An externally discovered Dickens novel.",
  sourceType: "external_discovery",
  providerId: "mock-open-library:bleak-house",
};

const externalDestination = {
  ...destinationFixture,
  id: "edinburgh",
  name: "Edinburgh",
  country: "Scotland",
  description: "An externally discovered literary city.",
  sourceType: "external_discovery",
  providerId: "mock-destination:edinburgh",
};

function createTestPinia() {
  const pinia = createPinia();
  setActivePinia(pinia);
  return pinia;
}

describe("authenticated catalog discovery UI", () => {
  beforeEach(() => {
    mocks.auth.canUseExternalDiscovery = false;
    mocks.discoverBooks.mockReset();
    mocks.discoverDestinations.mockReset();
    mocks.fetchBooksByDestination.mockReset();
    mocks.fetchDestinations.mockReset();
    mocks.fetchBooksByDestination.mockResolvedValue([bookFixture]);
    mocks.fetchDestinations.mockResolvedValue([destinationFixture]);
  });

  it("keeps anonymous book browsing repository-only", async () => {
    const pinia = createTestPinia();
    const wrapper = mount(BooksView, {
      global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } },
    });

    await flushPromises();

    expect(wrapper.text()).toContain("Oliver Twist");
    expect(
      wrapper.find('form[aria-label="Discover books beyond the public repository"]').exists(),
    ).toBe(false);
    expect(mocks.fetchBooksByDestination).toHaveBeenCalledWith("london");
    expect(mocks.discoverBooks).not.toHaveBeenCalled();
  });

  it("lets a capable user discover and select a missing book", async () => {
    mocks.auth.canUseExternalDiscovery = true;
    mocks.discoverBooks.mockResolvedValue({
      results: [externalBook],
      repositoryOnly: false,
      externalDiscoveryUsed: true,
    });
    const pinia = createTestPinia();
    const bookStore = useBookStore(pinia);
    const discoverSpy = vi.spyOn(bookStore, "discoverMissingBooks");
    const wrapper = mount(BooksView, {
      global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } },
    });
    await flushPromises();

    const form = wrapper.get(
      'form[aria-label="Discover books beyond the public repository"]',
    );
    await form.get("input").setValue("  Bleak House  ");
    await form.trigger("submit");
    await flushPromises();

    expect(discoverSpy).toHaveBeenCalledWith("london", "Bleak House");
    expect(mocks.discoverBooks).toHaveBeenCalledWith("Bleak House", "london");
    expect(wrapper.text()).toContain("Bleak House");
    const bookLink = wrapper
      .findAllComponents(RouterLinkStub)
      .find((link) => link.text().includes("Configure Bleak House Tour"));
    expect(bookLink?.props("to")).toEqual({
      name: "itinerary-config-selection",
      params: { destinationId: "london", bookId: "external-london-bleak-house" },
    });

    await bookLink?.trigger("click");
    expect(bookStore.selectedBookId).toBe("external-london-bleak-house");
  });

  it("lets a capable user discover a missing destination", async () => {
    mocks.auth.canUseExternalDiscovery = true;
    mocks.discoverDestinations.mockResolvedValue({
      results: [externalDestination],
      repositoryOnly: false,
      externalDiscoveryUsed: true,
    });
    const pinia = createTestPinia();
    const destinationStore = useDestinationStore(pinia);
    const discoverSpy = vi.spyOn(destinationStore, "discoverMissingDestinations");
    const wrapper = mount(DestinationsView, {
      global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } },
    });
    await flushPromises();

    const form = wrapper.get(
      'form[aria-label="Discover destinations beyond the public repository"]',
    );
    await form.get("input").setValue("  Edinburgh  ");
    await form.trigger("submit");
    await flushPromises();

    expect(discoverSpy).toHaveBeenCalledWith("Edinburgh");
    expect(mocks.discoverDestinations).toHaveBeenCalledWith("Edinburgh");
    expect(wrapper.text()).toContain("Edinburgh");
  });

  it("keeps anonymous destination browsing repository-only", async () => {
    const pinia = createTestPinia();
    const wrapper = mount(DestinationsView, {
      global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } },
    });

    await flushPromises();

    expect(wrapper.text()).toContain("London");
    expect(
      wrapper
        .find('form[aria-label="Discover destinations beyond the public repository"]')
        .exists(),
    ).toBe(false);
    expect(mocks.fetchDestinations).toHaveBeenCalledOnce();
    expect(mocks.discoverDestinations).not.toHaveBeenCalled();
  });
});

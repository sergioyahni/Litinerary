import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import {
  fetchItineraryDetail,
  fetchPublicItineraries,
  generateItinerary,
} from "../services/itinerariesApi";
import { itineraryFixture } from "../test/fixtures";
import { useItineraryRepositoryStore } from "./itineraryRepositoryStore";
import { useItineraryStore } from "./itineraryStore";

vi.mock("../services/itinerariesApi", () => ({
  fetchItineraryDetail: vi.fn(),
  fetchPublicItineraries: vi.fn(),
  generateItinerary: vi.fn(),
}));

describe("itinerary Pinia stores", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetchItineraryDetail).mockReset();
    vi.mocked(fetchPublicItineraries).mockReset();
    vi.mocked(generateItinerary).mockReset();
  });

  it("generates itineraries with configured duration and transportation", async () => {
    vi.mocked(generateItinerary).mockResolvedValue({
      itinerary: itineraryFixture,
      matchedExisting: true,
      message: "Returned an exact mock public itinerary match.",
    });
    const store = useItineraryStore();
    store.durationDays = 1;
    store.transportationMode = "walking";

    const response = await store.submitGeneration({
      destinationId: "london",
      bookId: "oliver-twist",
    });

    expect(generateItinerary).toHaveBeenCalledWith({
      destinationId: "london",
      bookId: "oliver-twist",
      durationDays: 1,
      transportationMode: "walking",
    });
    expect(response?.itinerary.id).toBe(itineraryFixture.id);
    expect(store.currentItinerary?.id).toBe(itineraryFixture.id);
    expect(store.hasItinerary).toBe(true);
    expect(store.hasValidItinerary).toBe(true);
    expect(store.isGenerating).toBe(false);
  });

  it("records itinerary generation errors", async () => {
    vi.mocked(generateItinerary).mockRejectedValue(new Error("Invalid book"));
    const store = useItineraryStore();
    store.currentItinerary = itineraryFixture;

    const response = await store.submitGeneration({
      destinationId: "london",
      bookId: "bad-book",
    });

    expect(response).toBeNull();
    expect(store.error).toBe("Invalid book");
    expect(store.isGenerating).toBe(false);
    expect(store.currentItinerary).toBeNull();
  });

  it("does not generate without destination and book IDs", async () => {
    const store = useItineraryStore();

    const response = await store.submitGeneration({
      destinationId: "",
      bookId: "",
    });

    expect(response).toBeNull();
    expect(generateItinerary).not.toHaveBeenCalled();
    expect(store.error).toBe("Choose a destination and book before generating an itinerary.");
  });

  it("loads public repository itineraries", async () => {
    vi.mocked(fetchPublicItineraries).mockResolvedValue([itineraryFixture]);
    const store = useItineraryRepositoryStore();

    await store.loadItineraries();

    expect(store.itineraries).toEqual([itineraryFixture]);
    expect(store.error).toBeNull();
    expect(store.isLoading).toBe(false);
  });

  it("loads itinerary detail into selected itinerary", async () => {
    vi.mocked(fetchItineraryDetail).mockResolvedValue(itineraryFixture);
    const store = useItineraryRepositoryStore();

    await store.loadItineraryDetail(itineraryFixture.id);

    expect(fetchItineraryDetail).toHaveBeenCalledWith(itineraryFixture.id);
    expect(store.selectedItinerary?.title).toBe("Oliver Twist in London");
  });

  it("records 404 itinerary detail errors", async () => {
    vi.mocked(fetchItineraryDetail).mockRejectedValue(new Error("Unknown itinerary"));
    const store = useItineraryRepositoryStore();
    store.selectedItinerary = itineraryFixture;

    const result = await store.loadItineraryDetail("not-real");

    expect(result).toBeNull();
    expect(fetchItineraryDetail).toHaveBeenCalledWith("not-real");
    expect(store.selectedItinerary).toBeNull();
    expect(store.error).toBe("Unknown itinerary");
  });

  it("handles missing itinerary detail IDs", async () => {
    const store = useItineraryRepositoryStore();

    const result = await store.loadItineraryDetail("");

    expect(result).toBeNull();
    expect(fetchItineraryDetail).not.toHaveBeenCalled();
    expect(store.error).toBe("Missing itinerary ID.");
  });

  it("records repository loading errors and clears stale list data", async () => {
    vi.mocked(fetchPublicItineraries).mockRejectedValue(new Error("Repository down"));
    const store = useItineraryRepositoryStore();
    store.itineraries = [itineraryFixture];

    await store.loadItineraries();

    expect(store.itineraries).toEqual([]);
    expect(store.error).toBe("Repository down");
    expect(store.isLoading).toBe(false);
  });

  it("resets repository state", () => {
    const store = useItineraryRepositoryStore();
    store.itineraries = [itineraryFixture];
    store.selectedItinerary = itineraryFixture;
    store.error = "Old error";

    store.reset();

    expect(store.itineraries).toEqual([]);
    expect(store.selectedItinerary).toBeNull();
    expect(store.error).toBeNull();
  });
});

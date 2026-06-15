import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import {
  bookmarkItinerary,
  createUser,
  fetchUser,
  fetchUserBookmarks,
  fetchUserReviews,
  removeItineraryBookmark,
  saveUserPreference,
  saveUserReview,
} from "../services/usersApi";
import { itineraryFixture } from "../test/fixtures";
import { useUserStore } from "./userStore";

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

describe("userStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(bookmarkItinerary).mockReset();
    vi.mocked(createUser).mockReset();
    vi.mocked(fetchUser).mockReset();
    vi.mocked(fetchUserBookmarks).mockReset();
    vi.mocked(fetchUserReviews).mockReset();
    vi.mocked(removeItineraryBookmark).mockReset();
    vi.mocked(saveUserPreference).mockReset();
    vi.mocked(saveUserReview).mockReset();
  });

  it("creates a development user when one cannot be fetched", async () => {
    vi.mocked(fetchUser).mockRejectedValue(new Error("Unknown user"));
    vi.mocked(createUser).mockResolvedValue({
      id: "dev-reader",
      displayName: "Development Reader",
      createdAt: "now",
      preferences: [],
      reviews: [],
    });
    const store = useUserStore();

    await store.ensureDevelopmentUser();

    expect(createUser).toHaveBeenCalledWith({
      id: "dev-reader",
      displayName: "Development Reader",
    });
    expect(store.profile?.id).toBe("dev-reader");
  });

  it("saves preferences and refreshes profile", async () => {
    vi.mocked(fetchUser).mockResolvedValue({
      id: "dev-reader",
      createdAt: "now",
      preferences: [],
      reviews: [],
    });
    vi.mocked(saveUserPreference).mockResolvedValue({
      id: "pref-1",
      userId: "dev-reader",
      key: "travel",
      value: { pace: "slow" },
      createdAt: "now",
    });
    const store = useUserStore();

    const saved = await store.savePreferences({ pace: "slow" });

    expect(saved).toBe(true);
    expect(saveUserPreference).toHaveBeenCalledWith("dev-reader", {
      key: "travel",
      value: { pace: "slow" },
    });
  });

  it("toggles bookmarks", async () => {
    vi.mocked(fetchUser).mockResolvedValue({
      id: "dev-reader",
      createdAt: "now",
      preferences: [],
      reviews: [],
    });
    vi.mocked(bookmarkItinerary).mockResolvedValue({
      userId: "dev-reader",
      itineraries: [itineraryFixture],
    });
    vi.mocked(removeItineraryBookmark).mockResolvedValue({
      userId: "dev-reader",
      itineraries: [],
    });
    const store = useUserStore();

    const bookmarked = await store.toggleBookmark(itineraryFixture);
    const removed = await store.toggleBookmark(itineraryFixture);

    expect(bookmarked).toBe(true);
    expect(removed).toBe(true);
    expect(bookmarkItinerary).toHaveBeenCalledWith("dev-reader", itineraryFixture.id);
    expect(removeItineraryBookmark).toHaveBeenCalledWith("dev-reader", itineraryFixture.id);
    expect(store.bookmarks).toEqual([]);
  });

  it("records failed bookmark actions", async () => {
    vi.mocked(fetchUser).mockResolvedValue({
      id: "dev-reader",
      createdAt: "now",
      preferences: [],
      reviews: [],
    });
    vi.mocked(bookmarkItinerary).mockRejectedValue(new Error("Forbidden"));
    const store = useUserStore();

    const bookmarked = await store.toggleBookmark(itineraryFixture);

    expect(bookmarked).toBe(false);
    expect(store.error).toBe("Forbidden");
    expect(store.isLoading).toBe(false);
  });

  it("submits reviews and refreshes review/profile state", async () => {
    vi.mocked(fetchUser).mockResolvedValue({
      id: "dev-reader",
      createdAt: "now",
      preferences: [],
      reviews: [],
    });
    vi.mocked(saveUserReview).mockResolvedValue({
      id: "review-1",
      userId: "dev-reader",
      itineraryId: itineraryFixture.id,
      rating: 5,
      comment: "Useful",
      createdAt: "now",
    });
    vi.mocked(fetchUserReviews).mockResolvedValue([]);
    const store = useUserStore();

    const submitted = await store.submitReview(itineraryFixture.id, 5, "Useful");

    expect(submitted).toBe(true);
    expect(saveUserReview).toHaveBeenCalledWith("dev-reader", {
      itineraryId: itineraryFixture.id,
      rating: 5,
      comment: "Useful",
    });
  });

  it("records failed review submissions", async () => {
    vi.mocked(fetchUser).mockResolvedValue({
      id: "dev-reader",
      createdAt: "now",
      preferences: [],
      reviews: [],
    });
    vi.mocked(saveUserReview).mockRejectedValue(new Error("Review rejected"));
    const store = useUserStore();

    const submitted = await store.submitReview(itineraryFixture.id, 5, "Useful");

    expect(submitted).toBe(false);
    expect(store.error).toBe("Review rejected");
    expect(store.isLoading).toBe(false);
  });

  it("does not submit reviews without an itinerary ID", async () => {
    const store = useUserStore();

    const submitted = await store.submitReview("", 5, "Useful");

    expect(submitted).toBe(false);
    expect(saveUserReview).not.toHaveBeenCalled();
    expect(store.error).toBe("Missing itinerary ID for review.");
  });

  it("resets user state", () => {
    const store = useUserStore();
    store.bookmarks = [itineraryFixture];
    store.error = "Old error";

    store.reset();

    expect(store.profile).toBeNull();
    expect(store.bookmarks).toEqual([]);
    expect(store.reviews).toEqual([]);
    expect(store.error).toBeNull();
  });
});

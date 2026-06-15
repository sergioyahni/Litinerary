import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { fetchBooksByDestination } from "../services/booksApi";
import { fetchDestinations } from "../services/destinationsApi";
import { bookFixture, destinationFixture } from "../test/fixtures";
import { useBookStore } from "./bookStore";
import { useDestinationStore } from "./destinationStore";

vi.mock("../services/booksApi", () => ({
  fetchBooksByDestination: vi.fn(),
}));

vi.mock("../services/destinationsApi", () => ({
  fetchDestinations: vi.fn(),
}));

describe("catalog Pinia stores", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetchBooksByDestination).mockReset();
    vi.mocked(fetchDestinations).mockReset();
  });

  it("loads destinations and exposes the selected destination", async () => {
    vi.mocked(fetchDestinations).mockResolvedValue([destinationFixture]);
    const store = useDestinationStore();

    await store.loadDestinations();
    store.selectDestination("london");

    expect(store.isLoading).toBe(false);
    expect(store.error).toBeNull();
    expect(store.destinations).toEqual([destinationFixture]);
    expect(store.selectedDestination?.name).toBe("London");
    expect(store.hasDestinations).toBe(true);
  });

  it("records destination loading errors", async () => {
    vi.mocked(fetchDestinations).mockRejectedValue(new Error("API unavailable"));
    const store = useDestinationStore();

    await store.loadDestinations();

    expect(store.isLoading).toBe(false);
    expect(store.error).toBe("API unavailable");
    expect(store.destinations).toEqual([]);
  });

  it("handles an empty destination list", async () => {
    vi.mocked(fetchDestinations).mockResolvedValue([]);
    const store = useDestinationStore();

    await store.loadDestinations();

    expect(store.destinations).toEqual([]);
    expect(store.hasDestinations).toBe(false);
    expect(store.error).toBeNull();
    expect(store.isLoading).toBe(false);
  });

  it("resets destination state", () => {
    const store = useDestinationStore();
    store.destinations = [destinationFixture];
    store.selectDestination("london");
    store.error = "Old error";

    store.reset();

    expect(store.destinations).toEqual([]);
    expect(store.selectedDestinationId).toBeNull();
    expect(store.error).toBeNull();
  });

  it("loads books for a destination and resets the selected book", async () => {
    vi.mocked(fetchBooksByDestination).mockResolvedValue([bookFixture]);
    const store = useBookStore();
    store.selectBook("old-selection");

    await store.loadBooks("london");
    store.selectBook("oliver-twist");

    expect(fetchBooksByDestination).toHaveBeenCalledWith("london");
    expect(store.books).toEqual([bookFixture]);
    expect(store.selectedBook?.title).toBe("Oliver Twist");
    expect(store.hasBooks).toBe(true);
  });

  it("clears books when loading books fails", async () => {
    vi.mocked(fetchBooksByDestination).mockRejectedValue(new Error("No city"));
    const store = useBookStore();

    await store.loadBooks("atlantis");

    expect(store.books).toEqual([]);
    expect(store.error).toBe("No city");
    expect(store.isLoading).toBe(false);
  });

  it("handles an empty book list for a destination", async () => {
    vi.mocked(fetchBooksByDestination).mockResolvedValue([]);
    const store = useBookStore();

    await store.loadBooks("empty-city");

    expect(store.books).toEqual([]);
    expect(store.hasBooks).toBe(false);
    expect(store.selectedBook).toBeNull();
    expect(store.error).toBeNull();
  });

  it("clears and resets book state", () => {
    const store = useBookStore();
    store.books = [bookFixture];
    store.selectBook("oliver-twist");
    store.error = "Old error";

    store.clearBooks();

    expect(store.books).toEqual([]);
    expect(store.selectedBookId).toBeNull();
    expect(store.error).toBeNull();
  });
});

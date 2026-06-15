import { beforeEach, describe, expect, it, vi } from "vitest";
import { itineraryFixture } from "../test/fixtures";
import { requestJson } from "./apiClient";
import {
  bookmarkItinerary,
  createUser,
  fetchUserBookmarks,
  removeItineraryBookmark,
  saveUserPreference,
  saveUserReview,
} from "./usersApi";

vi.mock("./apiClient", () => ({
  requestJson: vi.fn(),
}));

const requestJsonMock = vi.mocked(requestJson);

describe("usersApi", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
  });

  it("creates development users", async () => {
    requestJsonMock.mockResolvedValue({ id: "dev-reader" });

    await createUser({ id: "dev-reader", displayName: "Development Reader" });

    expect(requestJsonMock).toHaveBeenCalledWith("/api/users", {
      method: "POST",
      body: JSON.stringify({ id: "dev-reader", displayName: "Development Reader" }),
    });
  });

  it("saves user preferences", async () => {
    requestJsonMock.mockResolvedValue({});

    await saveUserPreference("dev-reader", { key: "travel", value: { pace: "slow" } });

    expect(requestJsonMock).toHaveBeenCalledWith("/api/users/dev-reader/preferences", {
      method: "POST",
      body: JSON.stringify({ key: "travel", value: { pace: "slow" } }),
    });
  });

  it("bookmarks and removes itineraries", async () => {
    requestJsonMock.mockResolvedValue({ userId: "dev-reader", itineraries: [itineraryFixture] });

    await bookmarkItinerary("dev-reader", itineraryFixture.id);
    await removeItineraryBookmark("dev-reader", itineraryFixture.id);

    expect(requestJsonMock).toHaveBeenNthCalledWith(
      1,
      `/api/users/dev-reader/bookmarks/${itineraryFixture.id}`,
      { method: "POST" },
    );
    expect(requestJsonMock).toHaveBeenNthCalledWith(
      2,
      `/api/users/dev-reader/bookmarks/${itineraryFixture.id}`,
      { method: "DELETE" },
    );
  });

  it("unwraps bookmark response itineraries", async () => {
    requestJsonMock.mockResolvedValue({ userId: "dev-reader", itineraries: [itineraryFixture] });

    await expect(fetchUserBookmarks("dev-reader")).resolves.toEqual([itineraryFixture]);
  });

  it("saves user reviews", async () => {
    requestJsonMock.mockResolvedValue({});

    await saveUserReview("dev-reader", {
      itineraryId: itineraryFixture.id,
      rating: 5,
      comment: "Loved it",
    });

    expect(requestJsonMock).toHaveBeenCalledWith("/api/users/dev-reader/reviews", {
      method: "POST",
      body: JSON.stringify({
        itineraryId: itineraryFixture.id,
        rating: 5,
        comment: "Loved it",
      }),
    });
  });
});

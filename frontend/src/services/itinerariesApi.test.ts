import { beforeEach, describe, expect, it, vi } from "vitest";
import { itineraryFixture } from "../test/fixtures";
import { requestJson } from "./apiClient";
import {
  adaptItinerary,
  fetchItineraryDetail,
  fetchPublicItineraries,
  generateItinerary,
} from "./itinerariesApi";

vi.mock("./apiClient", () => ({
  requestJson: vi.fn(),
}));

const requestJsonMock = vi.mocked(requestJson);

describe("itinerariesApi", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
  });

  it("posts itinerary generation requests", async () => {
    requestJsonMock.mockResolvedValue({ itinerary: itineraryFixture, matchedExisting: true });

    const request = {
      destinationId: "london",
      bookId: "oliver-twist",
      durationDays: 1,
      transportationMode: "walking" as const,
    };

    await generateItinerary(request);

    expect(requestJsonMock).toHaveBeenCalledWith("/api/itinerary/generate", {
      method: "POST",
      body: JSON.stringify(request),
    });
  });

  it("posts adaptation requests", async () => {
    requestJsonMock.mockResolvedValue({ itinerary: itineraryFixture, matchedExisting: true });

    const request = {
      sourceItineraryId: "source-id",
      durationDays: 2,
      transportationMode: "public_transport" as const,
    };

    await adaptItinerary(request);

    expect(requestJsonMock).toHaveBeenCalledWith("/api/itineraries/adapt", {
      method: "POST",
      body: JSON.stringify(request),
    });
  });

  it("builds public itinerary query filters", async () => {
    requestJsonMock.mockResolvedValue([itineraryFixture]);

    await fetchPublicItineraries({
      cityId: "london",
      bookId: "oliver-twist",
      transportationMode: "walking",
    });

    expect(requestJsonMock).toHaveBeenCalledWith(
      "/api/itineraries?city_id=london&book_id=oliver-twist&transportation_mode=walking",
    );
  });

  it("encodes itinerary detail ids", async () => {
    requestJsonMock.mockResolvedValue(itineraryFixture);

    await fetchItineraryDetail("itinerary with spaces");

    expect(requestJsonMock).toHaveBeenCalledWith("/api/itineraries/itinerary%20with%20spaces");
  });
});

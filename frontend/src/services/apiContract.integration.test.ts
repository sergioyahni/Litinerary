import { afterEach, describe, expect, it, vi } from "vitest";
import { offlineReadinessFixture, sherlockGenerationResponseFixture, sherlockItineraryFixture } from "../test/fixtures";
import { requestJson, setAuthTokenProvider } from "./apiClient";
import {
  fetchItineraryDetail,
  fetchPublicItineraries,
  generateItinerary,
} from "./itinerariesApi";

function mockFetchJson(payload: unknown, init: { ok?: boolean; status?: number; statusText?: string } = {}) {
  return vi.fn().mockResolvedValue({
    ok: init.ok ?? true,
    status: init.status ?? 200,
    statusText: init.statusText ?? "OK",
    json: vi.fn().mockResolvedValue(payload),
  });
}

function expectSafePayload(payload: unknown): void {
  const dumped = JSON.stringify(payload);
  expect(dumped).not.toContain("Authorization");
  expect(dumped).not.toContain("rawProviderPayload");
  expect(dumped).not.toContain("raw_provider_payload");
  expect(dumped).not.toMatch(/sk-[A-Za-z0-9_-]{20,}/);
  expect(dumped).not.toMatch(/Bearer\s+[A-Za-z0-9._-]{20,}/i);
}

describe("Batch 3 API contract integration shapes", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    setAuthTokenProvider(null);
  });

  it("handles successful mock itinerary generation responses", async () => {
    const fetchMock = mockFetchJson(sherlockGenerationResponseFixture);
    vi.stubGlobal("fetch", fetchMock);

    const response = await generateItinerary({
      destinationId: "london",
      bookId: "sherlock-holmes",
      durationDays: 1,
      transportationMode: "walking",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/itinerary/generate",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          destinationId: "london",
          bookId: "sherlock-holmes",
          durationDays: 1,
          transportationMode: "walking",
        }),
      }),
    );
    expect(response.itinerary.providerName).toBe("mock_ai");
    expect(response.itinerary.days[0].stops[0].poi.name).toBe("Baker Street");
    expect(response.itinerary.days[0].routingProviderMetadata?.provider_name).toBe(
      "mock_routing",
    );
    expectSafePayload(response);
  });

  it("handles itinerary list and detail response shapes", async () => {
    const fetchMock = mockFetchJson([sherlockItineraryFixture]);
    vi.stubGlobal("fetch", fetchMock);

    const list = await fetchPublicItineraries({
      cityId: "london",
      bookId: "sherlock-holmes",
      transportationMode: "walking",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/itineraries?city_id=london&book_id=sherlock-holmes&transportation_mode=walking",
      expect.any(Object),
    );
    expect(list[0].title).toBe("The Adventures of Sherlock Holmes in London");
    expectSafePayload(list);

    vi.stubGlobal("fetch", mockFetchJson(sherlockItineraryFixture));
    const detail = await fetchItineraryDetail(sherlockItineraryFixture.id);

    expect(detail.days[0].stops[0].poi.provenanceMetadata?.externalProviderUsed).toBe(false);
    expect(detail.provenanceMetadata?.provider_name).toBe("mock_ai");
    expectSafePayload(detail);
  });

  it("handles readiness response shape without enabling live providers", async () => {
    const fetchMock = mockFetchJson(offlineReadinessFixture);
    vi.stubGlobal("fetch", fetchMock);

    const readiness = await requestJson<typeof offlineReadinessFixture>("/api/readiness");

    expect(readiness.status).toBe("ready");
    expect(readiness.checks.externalCalls.allowed).toBe(false);
    expect(readiness.checks.providers[0].mode).toBe("mock");
    expect(readiness.checks.providers[0].realEnabled).toBe(false);
    expectSafePayload(readiness);
  });

  it("normalizes validation and provider-unavailable error payloads", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetchJson(
        { detail: "Book 'les-miserables' is not available for destination 'london'" },
        { ok: false, status: 400, statusText: "Bad Request" },
      ),
    );

    await expect(
      generateItinerary({
        destinationId: "london",
        bookId: "les-miserables",
        durationDays: 1,
        transportationMode: "walking",
      }),
    ).rejects.toMatchObject({
      status: 400,
      detail: "Book 'les-miserables' is not available for destination 'london'",
    });

    vi.stubGlobal(
      "fetch",
      mockFetchJson(
        { detail: { message: "External provider calls are blocked by ALLOW_EXTERNAL_CALLS=false." } },
        { ok: false, status: 503, statusText: "Service Unavailable" },
      ),
    );

    await expect(requestJson("/api/itinerary/generate")).rejects.toMatchObject({
      status: 503,
      detail: "External provider calls are blocked by ALLOW_EXTERNAL_CALLS=false.",
    });
  });

  it("surfaces rejected fetch failures without creating secret-bearing payloads", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network failure")));

    await expect(requestJson("/api/readiness")).rejects.toThrow("Network failure");
  });
});

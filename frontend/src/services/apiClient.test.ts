import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, requestJson, setAuthTokenProvider } from "./apiClient";

describe("requestJson", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    setAuthTokenProvider(null);
  });

  it("returns parsed JSON for successful responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ status: "ok" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(requestJson("/api/health")).resolves.toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/health",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
  });

  it("throws ApiError with backend detail for failed responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: vi.fn().mockResolvedValue({ detail: "Unknown destination: atlantis" }),
      }),
    );

    await expect(requestJson("/api/books?city_id=atlantis")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      detail: "Unknown destination: atlantis",
    } satisfies Partial<ApiError>);
  });

  it("attaches bearer tokens when an auth token provider is configured", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ status: "ok" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    setAuthTokenProvider(() => "dev:reader:user:none");

    await requestJson("/api/users/reader");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/users/reader",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer dev:reader:user:none",
        }),
      }),
    );
  });

  it("marks 401 and 403 ApiErrors for auth handling", async () => {
    const unauthorized = new ApiError(401, "Authentication is required.");
    const forbidden = new ApiError(403, "Forbidden.");

    expect(unauthorized.isUnauthorized).toBe(true);
    expect(unauthorized.isForbidden).toBe(false);
    expect(forbidden.isUnauthorized).toBe(false);
    expect(forbidden.isForbidden).toBe(true);
  });
});

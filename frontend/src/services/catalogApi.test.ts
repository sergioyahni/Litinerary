import { beforeEach, describe, expect, it, vi } from "vitest";
import { requestJson } from "./apiClient";
import { fetchBooksByDestination } from "./booksApi";
import { fetchDestinations } from "./destinationsApi";

vi.mock("./apiClient", () => ({
  requestJson: vi.fn(),
}));

const requestJsonMock = vi.mocked(requestJson);

describe("catalog API services", () => {
  beforeEach(() => {
    requestJsonMock.mockReset();
  });

  it("fetches destinations from the API", async () => {
    requestJsonMock.mockResolvedValue([]);

    await fetchDestinations();

    expect(requestJsonMock).toHaveBeenCalledWith("/api/destinations");
  });

  it("fetches books by destination using the city query parameter", async () => {
    requestJsonMock.mockResolvedValue([]);

    await fetchBooksByDestination("new york");

    expect(requestJsonMock).toHaveBeenCalledWith("/api/books?city_id=new+york");
  });
});

import type {
  Itinerary,
  ItineraryAdaptationRequest,
  ItineraryGenerationRequest,
  ItineraryGenerationResponse,
  ItineraryNarration,
  NarrationRequest,
  TransportationMode,
} from "../types";
import { requestJson } from "./apiClient";

interface FetchItineraryFilters {
  cityId?: string;
  bookId?: string;
  transportationMode?: TransportationMode;
}

export function generateItinerary(
  request: ItineraryGenerationRequest,
): Promise<ItineraryGenerationResponse> {
  return requestJson<ItineraryGenerationResponse>("/api/itinerary/generate", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function adaptItinerary(
  request: ItineraryAdaptationRequest,
): Promise<ItineraryGenerationResponse> {
  return requestJson<ItineraryGenerationResponse>("/api/itineraries/adapt", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function fetchPublicItineraries(
  filters: FetchItineraryFilters = {},
): Promise<Itinerary[]> {
  const params = new URLSearchParams();

  if (filters.cityId) {
    params.set("city_id", filters.cityId);
  }

  if (filters.bookId) {
    params.set("book_id", filters.bookId);
  }

  if (filters.transportationMode) {
    params.set("transportation_mode", filters.transportationMode);
  }

  const query = params.toString();
  return requestJson<Itinerary[]>(`/api/itineraries${query ? `?${query}` : ""}`);
}

export function fetchItineraryDetail(itineraryId: string): Promise<Itinerary> {
  return requestJson<Itinerary>(`/api/itineraries/${encodeURIComponent(itineraryId)}`);
}

export function fetchItineraryNarration(itineraryId: string): Promise<ItineraryNarration> {
  return requestJson<ItineraryNarration>(
    `/api/itineraries/${encodeURIComponent(itineraryId)}/narration`,
  );
}

export function generateItineraryNarration(
  itineraryId: string,
  request: NarrationRequest = {},
): Promise<ItineraryNarration> {
  return requestJson<ItineraryNarration>(
    `/api/itineraries/${encodeURIComponent(itineraryId)}/narration`,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

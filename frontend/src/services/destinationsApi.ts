import type { Destination, DiscoverySearchResponse } from "../types";
import { requestJson } from "./apiClient";

export function fetchDestinations(): Promise<Destination[]> {
  return requestJson<Destination[]>("/api/destinations");
}

export function searchPublicDestinations(query: string): Promise<Destination[]> {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  return requestJson<Destination[]>(`/api/destinations?${params.toString()}`);
}

export function discoverDestinations(
  query: string,
): Promise<DiscoverySearchResponse<Destination>> {
  const params = new URLSearchParams({ q: query });
  return requestJson<DiscoverySearchResponse<Destination>>(
    `/api/discovery/destinations?${params.toString()}`,
  );
}

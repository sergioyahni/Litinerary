import type { Book, DiscoverySearchResponse } from "../types";
import { requestJson } from "./apiClient";

export function fetchBooksByDestination(destinationId: string): Promise<Book[]> {
  const params = new URLSearchParams({ city_id: destinationId });
  return requestJson<Book[]>(`/api/books?${params.toString()}`);
}

export function searchPublicBooks(
  query: string,
  destinationId?: string | null,
): Promise<Book[]> {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (destinationId) params.set("city_id", destinationId);
  return requestJson<Book[]>(`/api/books?${params.toString()}`);
}

export function discoverBooks(
  query: string,
  destinationId?: string | null,
): Promise<DiscoverySearchResponse<Book>> {
  const params = new URLSearchParams({ q: query });
  if (destinationId) params.set("city_id", destinationId);
  return requestJson<DiscoverySearchResponse<Book>>(
    `/api/discovery/books?${params.toString()}`,
  );
}

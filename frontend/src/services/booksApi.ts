import type { Book } from "../types";
import { requestJson } from "./apiClient";

export function fetchBooksByDestination(destinationId: string): Promise<Book[]> {
  const params = new URLSearchParams({ city_id: destinationId });
  return requestJson<Book[]>(`/api/books?${params.toString()}`);
}

import type { Destination } from "../types";
import { requestJson } from "./apiClient";

export function fetchDestinations(): Promise<Destination[]> {
  return requestJson<Destination[]>("/api/destinations");
}

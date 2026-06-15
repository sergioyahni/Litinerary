import type {
  Itinerary,
  UserBookmarksResponse,
  UserCreateRequest,
  UserPreference,
  UserPreferenceUpsertRequest,
  UserProfile,
  UserReview,
  UserReviewCreateRequest,
} from "../types";
import { requestJson } from "./apiClient";

export function createUser(request: UserCreateRequest): Promise<UserProfile> {
  return requestJson<UserProfile>("/api/users", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function fetchUser(userId: string): Promise<UserProfile> {
  return requestJson<UserProfile>(`/api/users/${encodeURIComponent(userId)}`);
}

export function saveUserPreference(
  userId: string,
  request: UserPreferenceUpsertRequest,
): Promise<UserPreference> {
  return requestJson<UserPreference>(`/api/users/${encodeURIComponent(userId)}/preferences`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function bookmarkItinerary(
  userId: string,
  itineraryId: string,
): Promise<UserBookmarksResponse> {
  return requestJson<UserBookmarksResponse>(
    `/api/users/${encodeURIComponent(userId)}/bookmarks/${encodeURIComponent(itineraryId)}`,
    { method: "POST" },
  );
}

export function removeItineraryBookmark(
  userId: string,
  itineraryId: string,
): Promise<UserBookmarksResponse> {
  return requestJson<UserBookmarksResponse>(
    `/api/users/${encodeURIComponent(userId)}/bookmarks/${encodeURIComponent(itineraryId)}`,
    { method: "DELETE" },
  );
}

export async function fetchUserBookmarks(userId: string): Promise<Itinerary[]> {
  const response = await requestJson<UserBookmarksResponse>(
    `/api/users/${encodeURIComponent(userId)}/bookmarks`,
  );
  return response.itineraries;
}

export function saveUserReview(
  userId: string,
  request: UserReviewCreateRequest,
): Promise<UserReview> {
  return requestJson<UserReview>(`/api/users/${encodeURIComponent(userId)}/reviews`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function fetchUserReviews(userId: string): Promise<UserReview[]> {
  return requestJson<UserReview[]>(`/api/users/${encodeURIComponent(userId)}/reviews`);
}

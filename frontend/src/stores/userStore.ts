import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
  bookmarkItinerary,
  createUser,
  fetchUser,
  fetchUserBookmarks,
  fetchUserReviews,
  removeItineraryBookmark,
  saveUserPreference,
  saveUserReview,
} from "../services/usersApi";
import type { Itinerary, UserProfile, UserReview } from "../types";
import { useAuthStore } from "./authStore";

export const DEVELOPMENT_USER_ID = "dev-reader";

export const useUserStore = defineStore("user", () => {
  const authStore = useAuthStore();
  const profile = ref<UserProfile | null>(null);
  const bookmarks = ref<Itinerary[]>([]);
  const reviews = ref<UserReview[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const userId = computed(
    () => authStore.currentUserId ?? profile.value?.id ?? DEVELOPMENT_USER_ID,
  );
  const hasProfile = computed(() => profile.value !== null);
  const hasBookmarks = computed(() => bookmarks.value.length > 0);
  const hasReviews = computed(() => reviews.value.length > 0);

  async function ensureCurrentUser(): Promise<UserProfile | null> {
    if (authStore.isAuthEnabled) {
      if (!authStore.isAuthenticated) {
        authStore.handleApiError(new Error("Sign in to continue."));
        error.value = "Sign in to continue.";
        return null;
      }
      if (authStore.currentUser) {
        profile.value = authStore.currentUser;
        return profile.value;
      }
      profile.value = await authStore.hydrateAuthenticatedUser();
      if (!profile.value) {
        error.value = authStore.error ?? "Sign in to continue.";
      }
      return profile.value;
    }
    return ensureDevelopmentUser();
  }

  async function ensureDevelopmentUser(): Promise<UserProfile | null> {
    if (!authStore.canLoginWithDevelopmentToken && !authStore.isAuthenticated) {
      error.value = "Sign in to continue.";
      return null;
    }
    if (profile.value) {
      return profile.value;
    }

    isLoading.value = true;
    error.value = null;

    try {
      profile.value = await fetchUser(userId.value);
    } catch {
      try {
        profile.value = await createUser({
          id: userId.value,
          displayName: userId.value === DEVELOPMENT_USER_ID ? "Development Reader" : null,
        });
      } catch (caught) {
        authStore.handleApiError(caught);
        error.value =
          caught instanceof Error ? caught.message : "Unable to create development user.";
        return null;
      }
    } finally {
      isLoading.value = false;
    }

    return profile.value;
  }

  async function loadProfile(): Promise<void> {
    isLoading.value = true;
    error.value = null;

    try {
      if (authStore.isAuthEnabled) {
        profile.value = authStore.currentUser ?? (await authStore.hydrateAuthenticatedUser());
      } else {
        profile.value = await fetchUser(userId.value);
      }
    } catch (caught) {
      authStore.handleApiError(caught);
      error.value =
        caught instanceof Error
          ? caught.message
          : "No user profile is available yet.";
    } finally {
      isLoading.value = false;
    }
  }

  async function savePreferences(value: Record<string, unknown>): Promise<boolean> {
    const user = await ensureCurrentUser();
    if (!user) return false;

    isLoading.value = true;
    error.value = null;

    try {
      await saveUserPreference(user.id, { key: "travel", value });
      profile.value = await fetchUser(user.id);
      return true;
    } catch (caught) {
      authStore.handleApiError(caught);
      error.value = caught instanceof Error ? caught.message : "Unable to save preferences.";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function loadBookmarks(): Promise<void> {
    const user = await ensureCurrentUser();
    if (!user) return;

    isLoading.value = true;
    error.value = null;

    try {
      bookmarks.value = await fetchUserBookmarks(user.id);
    } catch (caught) {
      authStore.handleApiError(caught);
      error.value = caught instanceof Error ? caught.message : "Unable to load bookmarks.";
    } finally {
      isLoading.value = false;
    }
  }

  async function toggleBookmark(itinerary: Itinerary): Promise<boolean> {
    const user = await ensureCurrentUser();
    if (!user) return false;

    isLoading.value = true;
    error.value = null;

    try {
      const isBookmarked = bookmarks.value.some((item) => item.id === itinerary.id);
      const response = isBookmarked
        ? await removeItineraryBookmark(user.id, itinerary.id)
        : await bookmarkItinerary(user.id, itinerary.id);
      bookmarks.value = response.itineraries;
      return true;
    } catch (caught) {
      authStore.handleApiError(caught);
      error.value = caught instanceof Error ? caught.message : "Unable to update bookmark.";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function submitReview(
    itineraryId: string,
    rating: number,
    comment: string,
  ): Promise<boolean> {
    if (!itineraryId) {
      error.value = "Missing itinerary ID for review.";
      return false;
    }

    const user = await ensureCurrentUser();
    if (!user) return false;

    isLoading.value = true;
    error.value = null;

    try {
      await saveUserReview(user.id, { itineraryId, rating, comment });
      reviews.value = await fetchUserReviews(user.id);
      profile.value = await fetchUser(user.id);
      return true;
    } catch (caught) {
      authStore.handleApiError(caught);
      error.value = caught instanceof Error ? caught.message : "Unable to save review.";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  function isBookmarked(itineraryId: string): boolean {
    return bookmarks.value.some((itinerary) => itinerary.id === itineraryId);
  }

  function clearError(): void {
    error.value = null;
    authStore.lastAuthStatus = null;
  }

  function reset(): void {
    profile.value = null;
    bookmarks.value = [];
    reviews.value = [];
    isLoading.value = false;
    error.value = null;
  }

  return {
    profile,
    bookmarks,
    reviews,
    isLoading,
    error,
    userId,
    hasProfile,
    hasBookmarks,
    hasReviews,
    ensureDevelopmentUser,
    ensureCurrentUser,
    loadProfile,
    savePreferences,
    loadBookmarks,
    toggleBookmark,
    submitReview,
    isBookmarked,
    clearError,
    reset,
  };
});

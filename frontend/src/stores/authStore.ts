import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
  AUTH_RUNTIME_CONFIG,
  getAuthSession,
  loginWithDevelopmentSubscriberToken,
  loginWithDevelopmentToken,
  logout as logoutSession,
  refreshCurrentUserSession,
  setManagedAuthSession,
  type AuthSession,
} from "../services/authService";
import { ApiError } from "../services/apiClient";
import type { UserProfile } from "../types/domain";

export const useAuthStore = defineStore("auth", () => {
  const session = ref<AuthSession | null>(getAuthSession());
  const currentUser = ref<UserProfile | null>(null);
  const error = ref<string | null>(null);
  const lastAuthStatus = ref<401 | 403 | null>(null);

  const isAuthEnabled = computed(() => AUTH_RUNTIME_CONFIG.enabled);
  const isAuthenticated = computed(() => session.value !== null);
  const currentUserId = computed(() => session.value?.userId ?? null);
  const isAdmin = computed(() => session.value?.roles.includes("admin") ?? false);
  const isSubscriber = computed(
    () =>
      session.value?.subscriptionStatus === "active" ||
      session.value?.roles.includes("subscriber") ||
      false,
  );

  async function loginDevelopmentUser(userId = "dev-reader"): Promise<boolean> {
    error.value = null;
    try {
      session.value = await loginWithDevelopmentToken(userId);
      currentUser.value = null;
      lastAuthStatus.value = null;
      return true;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "Unable to log in.";
      return false;
    }
  }

  async function loginDevelopmentSubscriber(userId = "dev-subscriber"): Promise<boolean> {
    error.value = null;
    try {
      session.value = await loginWithDevelopmentSubscriberToken(userId);
      currentUser.value = null;
      lastAuthStatus.value = null;
      return true;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "Unable to log in.";
      return false;
    }
  }

  async function acceptManagedToken(token: string): Promise<boolean> {
    error.value = null;
    try {
      session.value = setManagedAuthSession(token);
      const refreshed = await refreshCurrentUserSession();
      session.value = refreshed.session;
      currentUser.value = refreshed.profile;
      lastAuthStatus.value = null;
      return true;
    } catch (caught) {
      session.value = null;
      currentUser.value = null;
      handleApiError(caught);
      return false;
    }
  }

  async function loadCurrentUser(): Promise<UserProfile | null> {
    error.value = null;
    try {
      const refreshed = await refreshCurrentUserSession();
      session.value = refreshed.session;
      currentUser.value = refreshed.profile;
      lastAuthStatus.value = null;
      return refreshed.profile;
    } catch (caught) {
      handleApiError(caught);
      if (caught instanceof ApiError && caught.isUnauthorized) {
        session.value = null;
        currentUser.value = null;
      }
      return null;
    }
  }

  async function logout(): Promise<void> {
    await logoutSession();
    session.value = null;
    currentUser.value = null;
    error.value = null;
    lastAuthStatus.value = null;
  }

  function handleApiError(caught: unknown): void {
    if (caught instanceof ApiError && (caught.isUnauthorized || caught.isForbidden)) {
      lastAuthStatus.value = caught.status as 401 | 403;
      error.value =
        caught.status === 401
          ? "Sign in to continue."
          : "You do not have permission to perform this action.";
      return;
    }
    error.value = caught instanceof Error ? caught.message : "Request failed.";
  }

  return {
    session,
    currentUser,
    error,
    lastAuthStatus,
    isAuthEnabled,
    isAuthenticated,
    currentUserId,
    isAdmin,
    isSubscriber,
    loginDevelopmentUser,
    loginDevelopmentSubscriber,
    acceptManagedToken,
    loadCurrentUser,
    logout,
    handleApiError,
  };
});

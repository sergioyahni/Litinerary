import { defineStore } from "pinia";
import { computed, ref } from "vue";
import {
  AUTH_RUNTIME_CONFIG,
  auth0ConfigurationErrors,
  canUseDevelopmentLogin,
  getAuthSession,
  hydrateAuth0User,
  loginWithDevelopmentSubscriberToken,
  loginWithDevelopmentToken,
  loginWithAuth0,
  logout as logoutSession,
  refreshCurrentUserSession,
  restoreAuth0Session,
  setManagedAuthSessionFromToken,
  usesAuth0,
  type AuthSession,
} from "../services/authService";
import { ApiError } from "../services/apiClient";
import type { UserProfile } from "../types/domain";

export const useAuthStore = defineStore("auth", () => {
  const session = ref<AuthSession | null>(getAuthSession());
  const currentUser = ref<UserProfile | null>(null);
  const error = ref<string | null>(null);
  const lastAuthStatus = ref<401 | 403 | null>(null);
  const isInitializing = ref(false);

  const isAuthEnabled = computed(() => AUTH_RUNTIME_CONFIG.enabled);
  const isAuth0Enabled = computed(() => usesAuth0());
  const isAuth0Configured = computed(() => auth0ConfigurationErrors().length === 0);
  const canLoginWithDevelopmentToken = computed(() => canUseDevelopmentLogin());
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
      session.value = setManagedAuthSessionFromToken(token);
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

  async function login(target?: string): Promise<boolean> {
    error.value = null;
    try {
      if (usesAuth0()) {
        await loginWithAuth0(target);
        return true;
      }
      await loginDevelopmentUser();
      return true;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "Unable to start sign in.";
      return false;
    }
  }

  async function restoreSession(): Promise<UserProfile | null> {
    if (!usesAuth0()) {
      return null;
    }
    isInitializing.value = true;
    error.value = null;
    try {
      const restored = await restoreAuth0Session();
      session.value = restored.session;
      currentUser.value = restored.profile;
      lastAuthStatus.value = null;
      return restored.profile;
    } catch (caught) {
      session.value = null;
      currentUser.value = null;
      error.value = friendlyAuth0Error(caught);
      return null;
    } finally {
      isInitializing.value = false;
    }
  }

  async function hydrateAuthenticatedUser(): Promise<UserProfile | null> {
    if (!usesAuth0()) {
      return loadCurrentUser();
    }
    isInitializing.value = true;
    error.value = null;
    try {
      const hydrated = await hydrateAuth0User();
      session.value = hydrated.session;
      currentUser.value = hydrated.profile;
      lastAuthStatus.value = null;
      return hydrated.profile;
    } catch (caught) {
      handleApiError(caught);
      if (caught instanceof ApiError && caught.isUnauthorized) {
        session.value = null;
        currentUser.value = null;
      }
      return null;
    } finally {
      isInitializing.value = false;
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
      if (caught.isUnauthorized) {
        session.value = null;
        currentUser.value = null;
      }
      error.value =
        caught.status === 401
          ? "Sign in to continue."
          : "You do not have permission to perform this action.";
      return;
    }
    error.value = caught instanceof Error ? caught.message : "Request failed.";
  }

  function friendlyAuth0Error(caught: unknown): string {
    const message = caught instanceof Error ? caught.message : "Authentication session could not be restored.";
    if (message.includes("Auth0 frontend configuration is incomplete")) {
      return message;
    }
    return "Sign in to continue.";
  }

  return {
    session,
    currentUser,
    error,
    lastAuthStatus,
    isInitializing,
    isAuthEnabled,
    isAuth0Enabled,
    isAuth0Configured,
    canLoginWithDevelopmentToken,
    isAuthenticated,
    currentUserId,
    isAdmin,
    isSubscriber,
    login,
    restoreSession,
    hydrateAuthenticatedUser,
    loginDevelopmentUser,
    loginDevelopmentSubscriber,
    acceptManagedToken,
    loadCurrentUser,
    logout,
    handleApiError,
  };
});

import type { UserProfile } from "../types/domain";
import { requestJson, setAuthTokenProvider } from "./apiClient";
import type { Auth0VueClient } from "@auth0/auth0-vue";
import { watch } from "vue";

export interface AuthSession {
  token: string | null;
  userId: string;
  roles: string[];
  subscriptionStatus: string;
  provider: string;
  source: "auth0" | "development";
}

export interface AuthRuntimeConfig {
  enabled: boolean;
  provider: string;
  allowDevLogin: boolean;
  auth0Domain: string;
  auth0ClientId: string;
  auth0Audience: string;
  auth0CallbackUrl: string;
  auth0LogoutReturnUrl: string;
  auth0UseRefreshTokens: boolean;
  auth0CacheLocation: "memory" | "localstorage";
}

export interface Auth0SessionResult {
  session: AuthSession | null;
  profile: UserProfile | null;
}

export const AUTH_RUNTIME_CONFIG: AuthRuntimeConfig = {
  enabled: import.meta.env.VITE_ENABLE_AUTH === "true",
  provider: (import.meta.env.VITE_AUTH_PROVIDER ?? "dev").toLowerCase(),
  allowDevLogin: import.meta.env.VITE_AUTH_ALLOW_DEV_LOGIN !== "false",
  auth0Domain: import.meta.env.VITE_AUTH0_DOMAIN ?? "",
  auth0ClientId: import.meta.env.VITE_AUTH0_CLIENT_ID ?? "",
  auth0Audience: import.meta.env.VITE_AUTH0_AUDIENCE ?? "",
  auth0CallbackUrl: import.meta.env.VITE_AUTH0_CALLBACK_URL ?? "",
  auth0LogoutReturnUrl: import.meta.env.VITE_AUTH0_LOGOUT_RETURN_URL ?? "",
  auth0UseRefreshTokens: import.meta.env.VITE_AUTH0_USE_REFRESH_TOKENS === "true",
  auth0CacheLocation:
    import.meta.env.VITE_AUTH0_CACHE_LOCATION === "localstorage" ? "localstorage" : "memory",
};

let currentSession: AuthSession | null = null;
let auth0Client: Auth0VueClient | null = null;

setAuthTokenProvider(async () => {
  if (usesAuth0()) {
    return acquireAuth0AccessToken({ allowAnonymous: true });
  }
  return currentSession?.token ?? null;
});

export function getAuthSession(): AuthSession | null {
  return currentSession;
}

export function usesAuth0(): boolean {
  return AUTH_RUNTIME_CONFIG.enabled && AUTH_RUNTIME_CONFIG.provider === "auth0";
}

export function canUseDevelopmentLogin(): boolean {
  return (
    AUTH_RUNTIME_CONFIG.allowDevLogin &&
    (!AUTH_RUNTIME_CONFIG.enabled || AUTH_RUNTIME_CONFIG.provider === "dev")
  );
}

export function auth0ConfigurationErrors(): string[] {
  if (!usesAuth0()) {
    return [];
  }
  const errors: string[] = [];
  if (!AUTH_RUNTIME_CONFIG.auth0Domain) errors.push("VITE_AUTH0_DOMAIN");
  if (!AUTH_RUNTIME_CONFIG.auth0ClientId) errors.push("VITE_AUTH0_CLIENT_ID");
  if (!AUTH_RUNTIME_CONFIG.auth0Audience) errors.push("VITE_AUTH0_AUDIENCE");
  if (!AUTH_RUNTIME_CONFIG.auth0CallbackUrl) errors.push("VITE_AUTH0_CALLBACK_URL");
  if (!AUTH_RUNTIME_CONFIG.auth0LogoutReturnUrl) {
    errors.push("VITE_AUTH0_LOGOUT_RETURN_URL");
  }
  return errors;
}

export function isAuth0Configured(): boolean {
  return auth0ConfigurationErrors().length === 0;
}

export function setAuth0Client(client: Auth0VueClient | null): void {
  auth0Client = client;
}

export function setManagedAuthSessionFromToken(
  token: string,
  profile?: Partial<UserProfile>,
): AuthSession {
  currentSession = {
    token,
    userId: profile?.id ?? "",
    roles: profile?.role ? [profile.role] : ["user"],
    subscriptionStatus: profile?.subscriptionStatus ?? "none",
    provider: AUTH_RUNTIME_CONFIG.provider,
    source: "development",
  };
  return currentSession;
}

export async function fetchCurrentUserProfile(): Promise<UserProfile> {
  return requestJson<UserProfile>("/api/me");
}

export async function refreshCurrentUserSession(): Promise<{
  session: AuthSession;
  profile: UserProfile;
}> {
  const profile = await fetchCurrentUserProfile();
  if (!currentSession) {
    throw new Error("No auth session is available.");
  }
  currentSession = {
    ...currentSession,
    userId: profile.id,
    roles: profile.role ? [profile.role] : currentSession.roles,
    subscriptionStatus: profile.subscriptionStatus ?? currentSession.subscriptionStatus,
    provider: profile.authProvider ?? currentSession.provider,
  };
  return { session: currentSession, profile };
}

export async function restoreAuth0Session(): Promise<Auth0SessionResult> {
  if (!usesAuth0()) {
    return { session: currentSession, profile: null };
  }
  ensureAuth0ReadyForUse();
  await waitForAuth0Ready();
  if (!auth0Client?.isAuthenticated.value) {
    clearLocalAuthSession();
    return { session: null, profile: null };
  }
  return hydrateAuth0User();
}

export async function hydrateAuth0User(): Promise<Auth0SessionResult> {
  if (!usesAuth0()) {
    return { session: currentSession, profile: null };
  }
  ensureAuth0ReadyForUse();
  await acquireAuth0AccessToken({ allowAnonymous: false });
  const profile = await fetchCurrentUserProfile();
  currentSession = sessionFromProfile(profile);
  return { session: currentSession, profile };
}

export async function loginWithAuth0(target = window.location.pathname): Promise<void> {
  if (!usesAuth0()) {
    throw new Error("Auth0 login is not enabled.");
  }
  ensureAuth0ReadyForUse();
  await auth0Client?.loginWithRedirect({
    appState: { target },
    authorizationParams: {
      audience: AUTH_RUNTIME_CONFIG.auth0Audience,
      redirect_uri: AUTH_RUNTIME_CONFIG.auth0CallbackUrl,
    },
  });
}

export async function logoutAuth0(): Promise<void> {
  clearLocalAuthSession();
  if (!usesAuth0()) {
    return;
  }
  ensureAuth0ReadyForUse();
  await auth0Client?.logout({
    logoutParams: {
      returnTo: AUTH_RUNTIME_CONFIG.auth0LogoutReturnUrl,
    },
  });
}

export async function loginWithDevelopmentToken(
  userId = "dev-reader",
  roles: string[] = ["user"],
  subscriptionStatus = "none",
): Promise<AuthSession> {
  if (!canUseDevelopmentLogin()) {
    throw new Error("Development auth login is not enabled.");
  }

  currentSession = {
    token: `dev:${userId}:${roles.join(",")}:${subscriptionStatus}`,
    userId,
    roles,
    subscriptionStatus,
    provider: "dev",
    source: "development",
  };
  return currentSession;
}

export function loginWithDevelopmentSubscriberToken(
  userId = "dev-subscriber",
): Promise<AuthSession> {
  return loginWithDevelopmentToken(userId, ["user", "subscriber"], "active");
}

export async function logout(): Promise<void> {
  if (usesAuth0()) {
    await logoutAuth0();
    return;
  }
  clearLocalAuthSession();
}

export function clearLocalAuthSession(): void {
  currentSession = null;
}

function sessionFromProfile(profile: UserProfile): AuthSession {
  return {
    token: null,
    userId: profile.id,
    roles: profile.role ? [profile.role] : ["user"],
    subscriptionStatus: profile.subscriptionStatus ?? "none",
    provider: profile.authProvider ?? AUTH_RUNTIME_CONFIG.provider,
    source: "auth0",
  };
}

function ensureAuth0ReadyForUse(): void {
  const errors = auth0ConfigurationErrors();
  if (errors.length > 0) {
    throw new Error(`Auth0 frontend configuration is incomplete: ${errors.join(", ")}.`);
  }
  if (!auth0Client) {
    throw new Error("Auth0 client is not initialized.");
  }
}

async function waitForAuth0Ready(): Promise<void> {
  if (!auth0Client?.isLoading.value) {
    return;
  }
  await new Promise<void>((resolve) => {
    const stop = watch(
      () => auth0Client?.isLoading.value ?? false,
      (isLoading) => {
        if (!isLoading) {
          stop();
          resolve();
        }
      },
      { immediate: true },
    );
  });
}

async function acquireAuth0AccessToken({
  allowAnonymous,
}: {
  allowAnonymous: boolean;
}): Promise<string | null> {
  if (!usesAuth0() || !auth0Client || auth0ConfigurationErrors().length > 0) {
    return null;
  }
  await waitForAuth0Ready();
  if (!auth0Client.isAuthenticated.value) {
    clearLocalAuthSession();
    return null;
  }
  try {
    return await auth0Client.getAccessTokenSilently({
      authorizationParams: {
        audience: AUTH_RUNTIME_CONFIG.auth0Audience,
      },
    });
  } catch (caught) {
    clearLocalAuthSession();
    if (allowAnonymous) {
      return null;
    }
    throw caught;
  }
}

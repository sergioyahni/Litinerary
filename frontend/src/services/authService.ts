import type { UserProfile } from "../types/domain";
import { requestJson, setAuthTokenProvider } from "./apiClient";

export interface AuthSession {
  token: string;
  userId: string;
  roles: string[];
  subscriptionStatus: string;
  provider: string;
}

export interface AuthRuntimeConfig {
  enabled: boolean;
  provider: string;
  allowDevLogin: boolean;
  loginUrl: string;
  logoutUrl: string;
}

export const AUTH_RUNTIME_CONFIG: AuthRuntimeConfig = {
  enabled: import.meta.env.VITE_ENABLE_AUTH === "true",
  provider: import.meta.env.VITE_AUTH_PROVIDER ?? "dev",
  allowDevLogin: import.meta.env.VITE_AUTH_ALLOW_DEV_LOGIN !== "false",
  loginUrl: import.meta.env.VITE_AUTH_LOGIN_URL ?? "",
  logoutUrl: import.meta.env.VITE_AUTH_LOGOUT_URL ?? "",
};

let currentSession: AuthSession | null = null;

setAuthTokenProvider(() => currentSession?.token ?? null);

export function getAuthSession(): AuthSession | null {
  return currentSession;
}

export function setManagedAuthSession(
  token: string,
  profile?: Partial<UserProfile>,
): AuthSession {
  currentSession = {
    token,
    userId: profile?.id ?? "",
    roles: profile?.role ? [profile.role] : ["user"],
    subscriptionStatus: profile?.subscriptionStatus ?? "none",
    provider: AUTH_RUNTIME_CONFIG.provider,
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

export async function loginWithDevelopmentToken(
  userId = "dev-reader",
  roles: string[] = ["user"],
  subscriptionStatus = "none",
): Promise<AuthSession> {
  if (!AUTH_RUNTIME_CONFIG.allowDevLogin || AUTH_RUNTIME_CONFIG.provider !== "dev") {
    throw new Error("Development auth login is not enabled.");
  }

  currentSession = {
    token: `dev:${userId}:${roles.join(",")}:${subscriptionStatus}`,
    userId,
    roles,
    subscriptionStatus,
    provider: "dev",
  };
  return currentSession;
}

export function loginWithDevelopmentSubscriberToken(
  userId = "dev-subscriber",
): Promise<AuthSession> {
  return loginWithDevelopmentToken(userId, ["user", "subscriber"], "active");
}

export async function logout(): Promise<void> {
  currentSession = null;
}

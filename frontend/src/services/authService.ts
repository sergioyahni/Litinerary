import { setAuthTokenProvider } from "./apiClient";

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
}

export const AUTH_RUNTIME_CONFIG: AuthRuntimeConfig = {
  enabled: import.meta.env.VITE_ENABLE_AUTH === "true",
  provider: import.meta.env.VITE_AUTH_PROVIDER ?? "dev",
  allowDevLogin: import.meta.env.VITE_AUTH_ALLOW_DEV_LOGIN !== "false",
};

let currentSession: AuthSession | null = null;

setAuthTokenProvider(() => currentSession?.token ?? null);

export function getAuthSession(): AuthSession | null {
  return currentSession;
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

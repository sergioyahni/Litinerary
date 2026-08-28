import { afterEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import type { Auth0VueClient } from "@auth0/auth0-vue";

function response(payload: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(),
    json: vi.fn().mockResolvedValue(payload),
  } as unknown as Response;
}

async function loadAuthService(env: Record<string, string | undefined>) {
  vi.resetModules();
  vi.unstubAllEnvs();
  for (const [key, value] of Object.entries(env)) {
    if (value !== undefined) {
      vi.stubEnv(key, value);
    }
  }
  return import("./authService");
}

function auth0Client(overrides: Partial<Auth0VueClient> = {}): Auth0VueClient {
  return {
    isLoading: ref(false),
    isAuthenticated: ref(true),
    user: ref({ sub: "auth0|reader" }),
    idTokenClaims: ref(undefined),
    error: ref(null),
    loginWithPopup: vi.fn(),
    loginWithRedirect: vi.fn(),
    loginWithCustomTokenExchange: vi.fn(),
    handleRedirectCallback: vi.fn(),
    checkSession: vi.fn(),
    getAccessTokenSilently: vi.fn().mockResolvedValue("auth0.access.token"),
    getAccessTokenWithPopup: vi.fn(),
    logout: vi.fn(),
    getDpopNonce: vi.fn(),
    setDpopNonce: vi.fn(),
    generateDpopProof: vi.fn(),
    createFetcher: vi.fn(),
    mfa: {} as Auth0VueClient["mfa"],
    passkey: {} as Auth0VueClient["passkey"],
    myAccount: {} as Auth0VueClient["myAccount"],
    ...overrides,
  };
}

describe("authService Auth0 lifecycle", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("reports missing Auth0 frontend configuration without secrets", async () => {
    const service = await loadAuthService({
      VITE_ENABLE_AUTH: "true",
      VITE_AUTH_PROVIDER: "auth0",
    });

    expect(service.auth0ConfigurationErrors()).toEqual([
      "VITE_AUTH0_DOMAIN",
      "VITE_AUTH0_CLIENT_ID",
      "VITE_AUTH0_AUDIENCE",
      "VITE_AUTH0_CALLBACK_URL",
      "VITE_AUTH0_LOGOUT_RETURN_URL",
    ]);
    expect(service.isAuth0Configured()).toBe(false);
  });

  it("does not expose development login in Auth0 mode", async () => {
    const service = await loadAuthService({
      VITE_ENABLE_AUTH: "true",
      VITE_AUTH_PROVIDER: "auth0",
      VITE_AUTH_ALLOW_DEV_LOGIN: "false",
      VITE_AUTH0_DOMAIN: "auth.example.test",
      VITE_AUTH0_CLIENT_ID: "client-id",
      VITE_AUTH0_AUDIENCE: "litinerary-api",
      VITE_AUTH0_CALLBACK_URL: "http://localhost:5173/auth/callback",
      VITE_AUTH0_LOGOUT_RETURN_URL: "http://localhost:5173",
    });

    expect(service.canUseDevelopmentLogin()).toBe(false);
    await expect(service.loginWithDevelopmentToken()).rejects.toThrow(
      "Development auth login is not enabled.",
    );
  });

  it("starts Auth0 login with audience, callback, and target route", async () => {
    const service = await loadAuthService({
      VITE_ENABLE_AUTH: "true",
      VITE_AUTH_PROVIDER: "auth0",
      VITE_AUTH0_DOMAIN: "auth.example.test",
      VITE_AUTH0_CLIENT_ID: "client-id",
      VITE_AUTH0_AUDIENCE: "litinerary-api",
      VITE_AUTH0_CALLBACK_URL: "http://localhost:5173/auth/callback",
      VITE_AUTH0_LOGOUT_RETURN_URL: "http://localhost:5173",
    });
    const client = auth0Client();
    service.setAuth0Client(client);

    await service.loginWithAuth0("/account/bookmarks");

    expect(client.loginWithRedirect).toHaveBeenCalledWith({
      appState: { target: "/account/bookmarks" },
      authorizationParams: {
        audience: "litinerary-api",
        redirect_uri: "http://localhost:5173/auth/callback",
      },
    });
  });

  it("hydrates /api/me after restoring an authenticated Auth0 session", async () => {
    const service = await loadAuthService({
      VITE_ENABLE_AUTH: "true",
      VITE_AUTH_PROVIDER: "auth0",
      VITE_AUTH0_DOMAIN: "auth.example.test",
      VITE_AUTH0_CLIENT_ID: "client-id",
      VITE_AUTH0_AUDIENCE: "litinerary-api",
      VITE_AUTH0_CALLBACK_URL: "http://localhost:5173/auth/callback",
      VITE_AUTH0_LOGOUT_RETURN_URL: "http://localhost:5173",
    });
    const fetchMock = vi.fn().mockResolvedValue(
      response({
        id: "auth0-reader",
        email: "reader@example.test",
        displayName: "Reader",
        authProvider: "auth0",
        role: "subscriber",
        subscriptionStatus: "active",
        createdAt: "2026-06-15T00:00:00Z",
        preferences: [],
        reviews: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = auth0Client();
    service.setAuth0Client(client);

    const restored = await service.restoreAuth0Session();

    expect(client.getAccessTokenSilently).toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/me",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer auth0.access.token" }),
      }),
    );
    expect(restored.session?.userId).toBe("auth0-reader");
    expect(restored.session?.token).toBeNull();
    expect(restored.profile?.email).toBe("reader@example.test");
  });

  it("keeps anonymous API requests anonymous when no Auth0 session exists", async () => {
    const service = await loadAuthService({
      VITE_ENABLE_AUTH: "true",
      VITE_AUTH_PROVIDER: "auth0",
      VITE_AUTH0_DOMAIN: "auth.example.test",
      VITE_AUTH0_CLIENT_ID: "client-id",
      VITE_AUTH0_AUDIENCE: "litinerary-api",
      VITE_AUTH0_CALLBACK_URL: "http://localhost:5173/auth/callback",
      VITE_AUTH0_LOGOUT_RETURN_URL: "http://localhost:5173",
    });
    const fetchMock = vi.fn().mockResolvedValue(response({ status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    service.setAuth0Client(
      auth0Client({
        isAuthenticated: ref(false),
      }),
    );
    const { requestJson } = await import("./apiClient");

    await requestJson("/api/health");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/health",
      expect.objectContaining({
        headers: expect.not.objectContaining({ Authorization: expect.any(String) }),
      }),
    );
  });

  it("clears local state and uses the configured Auth0 logout return URL", async () => {
    const service = await loadAuthService({
      VITE_ENABLE_AUTH: "true",
      VITE_AUTH_PROVIDER: "auth0",
      VITE_AUTH0_DOMAIN: "auth.example.test",
      VITE_AUTH0_CLIENT_ID: "client-id",
      VITE_AUTH0_AUDIENCE: "litinerary-api",
      VITE_AUTH0_CALLBACK_URL: "http://localhost:5173/auth/callback",
      VITE_AUTH0_LOGOUT_RETURN_URL: "http://localhost:5173",
    });
    const client = auth0Client();
    service.setAuth0Client(client);

    await service.logout();

    expect(client.logout).toHaveBeenCalledWith({
      logoutParams: { returnTo: "http://localhost:5173" },
    });
    expect(service.getAuthSession()).toBeNull();
  });
});

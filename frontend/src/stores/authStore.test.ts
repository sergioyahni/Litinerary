import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { ApiError } from "../services/apiClient";
import { useAuthStore } from "./authStore";

describe("authStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it("supports development login and logout placeholders", async () => {
    const store = useAuthStore();

    const loggedIn = await store.loginDevelopmentUser("dev-reader");

    expect(loggedIn).toBe(true);
    expect(store.isAuthenticated).toBe(true);
    expect(store.currentUserId).toBe("dev-reader");

    await store.logout();

    expect(store.isAuthenticated).toBe(false);
    expect(store.currentUserId).toBeNull();
  });

  it("supports development subscriber login placeholders", async () => {
    const store = useAuthStore();

    const loggedIn = await store.loginDevelopmentSubscriber("dev-subscriber");

    expect(loggedIn).toBe(true);
    expect(store.isSubscriber).toBe(true);
    expect(store.currentUserId).toBe("dev-subscriber");
  });

  it("tracks 401 and 403 API errors", () => {
    const store = useAuthStore();

    store.handleApiError(new ApiError(401, "Authentication required"));
    expect(store.lastAuthStatus).toBe(401);
    expect(store.error).toBe("Sign in to continue.");

    store.handleApiError(new ApiError(403, "Forbidden"));
    expect(store.lastAuthStatus).toBe(403);
    expect(store.error).toBe("You do not have permission to perform this action.");
  });

  it("clears stale sessions on 401 without clearing valid sessions on 403", async () => {
    const store = useAuthStore();
    await store.loginDevelopmentUser("dev-reader");

    store.handleApiError(new ApiError(403, "Forbidden"));
    expect(store.isAuthenticated).toBe(true);

    store.handleApiError(new ApiError(401, "Authentication required"));
    expect(store.isAuthenticated).toBe(false);
  });

  it("accepts a managed token and syncs the current user profile", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(init?.headers).toMatchObject({ Authorization: "Bearer managed.jwt.token" });
      return {
        ok: true,
        json: async () => ({
          id: "auth0-reader",
          email: "reader@example.test",
          displayName: "Reader",
          authProvider: "oidc",
          role: "subscriber",
          subscriptionStatus: "active",
          createdAt: "2026-06-15T00:00:00Z",
          preferences: [],
          reviews: [],
        }),
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);
    const store = useAuthStore();

    const accepted = await store.acceptManagedToken("managed.jwt.token");

    expect(accepted).toBe(true);
    expect(store.currentUserId).toBe("auth0-reader");
    expect(store.currentUser?.email).toBe("reader@example.test");
    expect(store.isSubscriber).toBe(true);
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});

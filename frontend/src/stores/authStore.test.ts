import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { ApiError } from "../services/apiClient";
import { useAuthStore } from "./authStore";

describe("authStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
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
});

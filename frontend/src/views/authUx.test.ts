import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

async function loadSubscriberChatView(env: Record<string, string>) {
  vi.resetModules();
  vi.unstubAllEnvs();
  for (const [key, value] of Object.entries(env)) {
    vi.stubEnv(key, value);
  }
  return (await import("./SubscriberChatView.vue")).default;
}

describe("authenticated feature UX", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("does not show development subscriber login in deployed Auth0 mode", async () => {
    const SubscriberChatView = await loadSubscriberChatView({
      VITE_ENABLE_AUTH: "true",
      VITE_AUTH_PROVIDER: "auth0",
      VITE_AUTH_ALLOW_DEV_LOGIN: "false",
    });
    setActivePinia(createPinia());

    const wrapper = mount(SubscriberChatView);

    expect(wrapper.text()).toContain("Sign In");
    expect(wrapper.text()).not.toContain("Use Development Subscriber");
  });

  it("keeps the development subscriber helper available when auth is local-only", async () => {
    const SubscriberChatView = await loadSubscriberChatView({
      VITE_ENABLE_AUTH: "false",
      VITE_AUTH_PROVIDER: "dev",
      VITE_AUTH_ALLOW_DEV_LOGIN: "true",
    });
    setActivePinia(createPinia());

    const wrapper = mount(SubscriberChatView);

    expect(wrapper.text()).toContain("Use Development Subscriber");
  });
});

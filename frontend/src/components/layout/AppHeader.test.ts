import { mount, RouterLinkStub } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import AppHeader from "./AppHeader.vue";

vi.mock("../../stores/authStore", () => ({
  useAuthStore: () => ({
    currentUser: null,
    currentUserId: null,
    isAuthEnabled: false,
    isAuthenticated: false,
    isInitializing: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

afterEach(() => {
  document.body.innerHTML = "";
});

describe("AppHeader", () => {
  it("opens and closes the navigation from a compact menu button", async () => {
    const wrapper = mount(AppHeader, {
      attachTo: document.body,
      global: {
        mocks: {
          $route: { fullPath: "/" },
        },
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });
    const toggle = wrapper.get("button.nav-toggle");

    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(toggle.attributes("aria-label")).toBe("Open navigation menu");
    expect(wrapper.find("#main-navigation-panel").exists()).toBe(false);

    await toggle.trigger("click");

    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(toggle.attributes("aria-label")).toBe("Close navigation menu");
    expect(wrapper.find("#main-navigation-panel").exists()).toBe(true);

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await wrapper.vm.$nextTick();

    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(wrapper.find("#main-navigation-panel").exists()).toBe(false);
    expect(document.activeElement).toBe(toggle.element);

    await toggle.trigger("click");
    document.body.click();
    await wrapper.vm.$nextTick();

    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(wrapper.find("#main-navigation-panel").exists()).toBe(false);

    wrapper.unmount();
  });

  it("closes the panel after a navigation link is selected", async () => {
    const wrapper = mount(AppHeader, {
      global: {
        mocks: {
          $route: { fullPath: "/" },
        },
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await wrapper.get("button.nav-toggle").trigger("click");
    await wrapper.findAll("a.nav-link")[0].trigger("click");

    expect(wrapper.find("#main-navigation-panel").exists()).toBe(false);

    wrapper.unmount();
  });
});

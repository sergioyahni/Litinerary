import { mount, RouterLinkStub } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import MainNavigation from "./MainNavigation.vue";

describe("MainNavigation", () => {
  it("renders the menu as keyboard-operable accordion sections", async () => {
    const wrapper = mount(MainNavigation, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    const triggers = wrapper.findAll("button.nav-accordion-trigger");
    expect(triggers).toHaveLength(3);
    expect(triggers.map((trigger) => trigger.text())).toEqual(["Discover", "Plan", "Account"]);
    expect(triggers.every((trigger) => trigger.attributes("aria-expanded") === "true")).toBe(true);

    await triggers[0].trigger("click");

    expect(triggers[0].attributes("aria-expanded")).toBe("false");
    expect(wrapper.find("#nav-discover-panel").attributes("style")).toBe("display: none;");

    await triggers[0].trigger("click");
    expect(wrapper.find("#nav-discover-panel").attributes("style")).toBe("");

    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links.map((link) => link.text())).toEqual([
      "Home",
      "Destinations",
      "Books by City",
      "Configure Tour",
      "Public Repository",
      "Profile",
      "Bookmarks",
    ]);
    expect(links.map((link) => link.props("to"))).toEqual([
      { name: "home" },
      { name: "destinations" },
      { name: "books" },
      { name: "itinerary-config" },
      { name: "itinerary-repository" },
      { name: "user-profile" },
      { name: "user-bookmarks" },
    ]);

    await links[0].trigger("click");

    expect(wrapper.emitted("navigate")).toHaveLength(1);
  });
});

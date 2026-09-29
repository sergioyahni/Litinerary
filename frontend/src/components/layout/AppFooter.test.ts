import { mount, RouterLinkStub } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import AppFooter from "./AppFooter.vue";

describe("AppFooter", () => {
  it("links to the stable public repository instead of a sample itinerary", () => {
    const wrapper = mount(AppFooter, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    const links = wrapper.findAllComponents(RouterLinkStub);
    const routeTargets = links
      .map((link) => link.props("to"))
      .filter((target): target is Record<string, any> => typeof target === "object");

    expect(routeTargets.some((target) => target.params?.id === "sample")).toBe(false);
    expect(
      links.some(
        (link) => {
          const target = link.props("to");
          return (
            link.text() === "Public Repository" &&
            typeof target === "object" &&
            target.name === "itinerary-repository"
          );
        },
      ),
    ).toBe(true);
  });
});

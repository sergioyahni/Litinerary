import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { itineraryFixture } from "../../test/fixtures";
import type { ItineraryStop } from "../../types";
import ItineraryDayList from "./ItineraryDayList.vue";
import ItineraryNarration from "./ItineraryNarration.vue";
import ItineraryStopCard from "./ItineraryStopCard.vue";
import ItinerarySummary from "./ItinerarySummary.vue";

vi.mock("../../services/itinerariesApi", () => ({
  fetchItineraryNarration: vi.fn(() => Promise.reject(new Error("Narration unavailable"))),
  generateItineraryNarration: vi.fn(() => Promise.reject(new Error("Narration unavailable"))),
}));

describe("itinerary display components", () => {
  it("renders itinerary summary stats and source notes", () => {
    const wrapper = mount(ItinerarySummary, {
      props: { itinerary: itineraryFixture },
    });

    expect(wrapper.text()).toContain("Oliver Twist in London");
    expect(wrapper.text()).toContain("1 day");
    expect(wrapper.text()).toContain("walking");
    expect(wrapper.text()).toContain("Stops");
    expect(wrapper.text()).toContain("exact match");
    expect(wrapper.text()).toContain("Returned from the public repository.");
  });

  it("renders an empty state when no itinerary days are available", () => {
    const wrapper = mount(ItineraryDayList, {
      props: { days: [] },
    });

    expect(wrapper.text()).toContain("No itinerary days are available.");
  });

  it("renders day cards and stops for available days", () => {
    const wrapper = mount(ItineraryDayList, {
      props: { days: itineraryFixture.days },
    });

    expect(wrapper.text()).toContain("Markets, Alleys, and Dickens' London");
    expect(wrapper.text()).toContain("Smithfield Market");
  });

  it("renders stop logistics, ticketing, and coordinates", () => {
    const wrapper = mount(ItineraryStopCard, {
      props: { stop: itineraryFixture.days[0].stops[0] },
    });

    expect(wrapper.text()).toContain("Smithfield Market");
    expect(wrapper.text()).toContain("35 min");
    expect(wrapper.text()).toContain("Good morning starting point.");
    expect(wrapper.text()).toContain("Outdoor/public area; no ticket required.");
    expect(wrapper.text()).toContain("51.5188, -0.1026");
  });

  it("renders optional ticketing links without requiring them", () => {
    const stopWithTicketUrl: ItineraryStop = {
      ...itineraryFixture.days[0].stops[0],
      poi: {
        ...itineraryFixture.days[0].stops[0].poi,
        ticketingUrl: "https://example.test/tickets/smithfield-market",
      },
    };

    const withUrl = mount(ItineraryStopCard, {
      props: { stop: stopWithTicketUrl },
    });
    const withoutUrl = mount(ItineraryStopCard, {
      props: { stop: itineraryFixture.days[0].stops[0] },
    });

    expect(withUrl.get("a").attributes("href")).toBe(
      "https://example.test/tickets/smithfield-market",
    );
    expect(withoutUrl.find("a").exists()).toBe(false);
  });

  it("shows a coordinate empty state when stop coordinates are missing", () => {
    const stopWithoutCoordinates: ItineraryStop = {
      ...itineraryFixture.days[0].stops[0],
      poi: {
        ...itineraryFixture.days[0].stops[0].poi,
        latitude: Number.NaN,
      },
    };

    const wrapper = mount(ItineraryStopCard, {
      props: { stop: stopWithoutCoordinates },
    });

    expect(wrapper.text()).toContain("Coordinates unavailable for this stop.");
  });

  it("keeps itinerary narration usable when backend narration is unavailable", () => {
    const wrapper = mount(ItineraryNarration, {
      props: { itinerary: itineraryFixture },
    });

    expect(wrapper.text()).toContain("Narration");
    expect(wrapper.text()).toContain("Oliver Twist in London");
    expect(wrapper.text()).toContain("Markets, Alleys, and Dickens' London");
  });
});

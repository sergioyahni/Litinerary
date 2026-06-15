import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import {
  createChatSession,
  fetchChatSessions,
  refineChatItinerary,
  sendChatMessage,
} from "../services/subscriberChatApi";
import { itineraryFixture } from "../test/fixtures";
import type { ChatSession } from "../types";
import { useSubscriberChatStore } from "./subscriberChatStore";

vi.mock("../services/subscriberChatApi", () => ({
  createChatSession: vi.fn(),
  fetchChatSessions: vi.fn(),
  refineChatItinerary: vi.fn(),
  sendChatMessage: vi.fn(),
}));

const chatSessionFixture: ChatSession = {
  id: "chat-1",
  userId: "dev-subscriber",
  title: "Subscriber itinerary chat",
  status: "active",
  createdAt: "2026-06-14T00:00:00+00:00",
  updatedAt: "2026-06-14T00:00:00+00:00",
  provenanceMetadata: { mockOnly: true },
  messages: [
    {
      id: "msg-1",
      sessionId: "chat-1",
      role: "assistant",
      content: "Welcome.",
      createdAt: "2026-06-14T00:00:00+00:00",
    },
  ],
  itineraryReferences: [],
};

describe("subscriberChatStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(createChatSession).mockReset();
    vi.mocked(fetchChatSessions).mockReset();
    vi.mocked(refineChatItinerary).mockReset();
    vi.mocked(sendChatMessage).mockReset();
  });

  it("loads and selects subscriber chat sessions", async () => {
    vi.mocked(fetchChatSessions).mockResolvedValue([chatSessionFixture]);
    const store = useSubscriberChatStore();

    await store.loadSessions();

    expect(store.sessions).toEqual([chatSessionFixture]);
    expect(store.activeSession?.id).toBe("chat-1");
  });

  it("starts a mock subscriber chat session", async () => {
    vi.mocked(createChatSession).mockResolvedValue(chatSessionFixture);
    const store = useSubscriberChatStore();

    const session = await store.startSession("Subscriber itinerary chat");

    expect(createChatSession).toHaveBeenCalledWith({ title: "Subscriber itinerary chat" });
    expect(session?.id).toBe("chat-1");
    expect(store.hasSession).toBe(true);
  });

  it("sends messages through the chat API", async () => {
    const updatedSession = {
      ...chatSessionFixture,
      messages: [
        ...chatSessionFixture.messages,
        {
          id: "msg-2",
          sessionId: "chat-1",
          role: "user" as const,
          content: "Slow it down.",
          createdAt: "2026-06-14T00:01:00+00:00",
        },
      ],
    };
    vi.mocked(sendChatMessage).mockResolvedValue({
      session: updatedSession,
      messages: updatedSession.messages.slice(1),
    });
    const store = useSubscriberChatStore();
    store.activeSession = chatSessionFixture;

    const sent = await store.sendMessage("Slow it down.");

    expect(sent).toBe(true);
    expect(sendChatMessage).toHaveBeenCalledWith("chat-1", { content: "Slow it down." });
    expect(store.messages).toHaveLength(2);
  });

  it("stores the last mock itinerary refinement", async () => {
    vi.mocked(refineChatItinerary).mockResolvedValue({
      session: chatSessionFixture,
      itinerary: { ...itineraryFixture, id: "sub-itinerary", subscriberOnly: true },
      reference: {
        id: "chatref-1",
        sessionId: "chat-1",
        itineraryId: "sub-itinerary",
        sourceItineraryId: itineraryFixture.id,
        refinementPrompt: "Quieter route.",
        createdAt: "2026-06-14T00:02:00+00:00",
      },
      message: {
        id: "msg-3",
        sessionId: "chat-1",
        role: "assistant",
        content: "Created.",
        createdAt: "2026-06-14T00:02:00+00:00",
      },
    });
    const store = useSubscriberChatStore();
    store.activeSession = chatSessionFixture;

    const response = await store.refineItinerary({
      sourceItineraryId: itineraryFixture.id,
      prompt: "Quieter route.",
      durationDays: 1,
      transportationMode: "walking",
    });

    expect(response?.itinerary.id).toBe("sub-itinerary");
    expect(store.lastRefinement?.reference.itineraryId).toBe("sub-itinerary");
  });
});

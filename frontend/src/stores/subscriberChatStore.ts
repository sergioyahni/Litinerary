import { defineStore } from "pinia";
import { computed, ref } from "vue";
import type {
  ChatItineraryRefinementRequest,
  ChatItineraryRefinementResponse,
  ChatSession,
} from "../types";
import {
  createChatSession,
  fetchChatSessions,
  refineChatItinerary,
  sendChatMessage,
} from "../services/subscriberChatApi";

export const useSubscriberChatStore = defineStore("subscriber-chat", () => {
  const sessions = ref<ChatSession[]>([]);
  const activeSession = ref<ChatSession | null>(null);
  const lastRefinement = ref<ChatItineraryRefinementResponse | null>(null);
  const isLoading = ref(false);
  const isSending = ref(false);
  const isRefining = ref(false);
  const error = ref<string | null>(null);

  const messages = computed(() => activeSession.value?.messages ?? []);
  const hasSession = computed(() => activeSession.value !== null);

  async function loadSessions(): Promise<void> {
    isLoading.value = true;
    error.value = null;
    try {
      sessions.value = await fetchChatSessions();
      activeSession.value = sessions.value[0] ?? null;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "Unable to load chat sessions.";
      sessions.value = [];
      activeSession.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  async function startSession(title = "Subscriber itinerary chat"): Promise<ChatSession | null> {
    isLoading.value = true;
    error.value = null;
    try {
      const session = await createChatSession({ title });
      activeSession.value = session;
      sessions.value = [session, ...sessions.value.filter((item) => item.id !== session.id)];
      return session;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "Unable to start chat.";
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  async function sendMessage(content: string): Promise<boolean> {
    if (!activeSession.value) {
      error.value = "Start a subscriber chat session first.";
      return false;
    }
    isSending.value = true;
    error.value = null;
    try {
      const response = await sendChatMessage(activeSession.value.id, { content });
      activeSession.value = response.session;
      upsertSession(response.session);
      return true;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "Unable to send message.";
      return false;
    } finally {
      isSending.value = false;
    }
  }

  async function refineItinerary(
    request: ChatItineraryRefinementRequest,
  ): Promise<ChatItineraryRefinementResponse | null> {
    if (!activeSession.value) {
      error.value = "Start a subscriber chat session first.";
      return null;
    }
    isRefining.value = true;
    error.value = null;
    try {
      const response = await refineChatItinerary(activeSession.value.id, request);
      activeSession.value = response.session;
      lastRefinement.value = response;
      upsertSession(response.session);
      return response;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "Unable to refine itinerary.";
      return null;
    } finally {
      isRefining.value = false;
    }
  }

  function upsertSession(session: ChatSession): void {
    sessions.value = [session, ...sessions.value.filter((item) => item.id !== session.id)];
  }

  function reset(): void {
    sessions.value = [];
    activeSession.value = null;
    lastRefinement.value = null;
    error.value = null;
    isLoading.value = false;
    isSending.value = false;
    isRefining.value = false;
  }

  return {
    sessions,
    activeSession,
    lastRefinement,
    isLoading,
    isSending,
    isRefining,
    error,
    messages,
    hasSession,
    loadSessions,
    startSession,
    sendMessage,
    refineItinerary,
    reset,
  };
});

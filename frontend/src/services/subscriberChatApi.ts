import type {
  ChatItineraryRefinementRequest,
  ChatItineraryRefinementResponse,
  ChatMessageCreate,
  ChatMessageResponse,
  ChatSession,
  ChatSessionCreate,
} from "../types";
import { requestJson } from "./apiClient";

const CHAT_BASE = "/api/subscribers/chat/sessions";

export function createChatSession(request: ChatSessionCreate = {}): Promise<ChatSession> {
  return requestJson<ChatSession>(CHAT_BASE, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function fetchChatSessions(): Promise<ChatSession[]> {
  return requestJson<ChatSession[]>(CHAT_BASE);
}

export function fetchChatSession(sessionId: string): Promise<ChatSession> {
  return requestJson<ChatSession>(`${CHAT_BASE}/${encodeURIComponent(sessionId)}`);
}

export function sendChatMessage(
  sessionId: string,
  request: ChatMessageCreate,
): Promise<ChatMessageResponse> {
  return requestJson<ChatMessageResponse>(
    `${CHAT_BASE}/${encodeURIComponent(sessionId)}/messages`,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

export function refineChatItinerary(
  sessionId: string,
  request: ChatItineraryRefinementRequest,
): Promise<ChatItineraryRefinementResponse> {
  return requestJson<ChatItineraryRefinementResponse>(
    `${CHAT_BASE}/${encodeURIComponent(sessionId)}/refine-itinerary`,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

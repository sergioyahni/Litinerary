<template>
  <section class="page-banner">
    <div class="container">
      <h1>Subscriber Chat</h1>
      <p>Tailor a literary route with the mock assistant.</p>
    </div>
  </section>

  <section class="section-margin">
    <div class="container">
      <div v-if="!authStore.isSubscriber" class="placeholder-panel">
        <h2>Subscriber access required</h2>
        <p>This chat is available only to active subscribers. Payments and billing are not implemented.</p>
        <button
          v-if="authStore.isAuthEnabled"
          class="button compact-button"
          type="button"
          @click="authStore.loginDevelopmentSubscriber()"
        >
          Use Development Subscriber
        </button>
      </div>

      <div v-else class="subscriber-chat-layout">
        <aside class="chat-sidebar" aria-label="Chat sessions">
          <button class="button compact-button" type="button" @click="startSession">
            New Chat
          </button>
          <p v-if="chatStore.isLoading" class="muted">Loading chats...</p>
          <ul v-if="chatStore.sessions.length" class="chat-session-list">
            <li v-for="session in chatStore.sessions" :key="session.id">
              <button
                type="button"
                :class="{ active: session.id === chatStore.activeSession?.id }"
                @click="chatStore.activeSession = session"
              >
                {{ session.title }}
              </button>
            </li>
          </ul>
        </aside>

        <div class="chat-panel">
          <div v-if="chatStore.error" class="inline-error" role="alert">
            {{ chatStore.error }}
          </div>

          <div v-if="!chatStore.activeSession" class="placeholder-panel">
            <h2>No chat selected</h2>
            <p>Start a subscriber chat to refine an existing public itinerary.</p>
          </div>

          <template v-else>
            <div class="chat-transcript" aria-live="polite">
              <article
                v-for="message in chatStore.messages"
                :key="message.id"
                :class="['chat-message', message.role]"
              >
                <p class="eyebrow">{{ message.role }}</p>
                <p>{{ message.content }}</p>
              </article>
            </div>

            <form class="chat-form" @submit.prevent="sendMessage">
              <label for="chat-message">Message</label>
              <textarea id="chat-message" v-model="messageText" rows="3" />
              <button class="button compact-button" type="submit" :disabled="chatStore.isSending">
                Send
              </button>
            </form>

            <form class="chat-form" @submit.prevent="refineItinerary">
              <label for="source-itinerary">Source itinerary ID</label>
              <input id="source-itinerary" v-model="sourceItineraryId" type="text" />

              <label for="refinement-prompt">Refinement note</label>
              <textarea id="refinement-prompt" v-model="refinementPrompt" rows="3" />

              <div class="form-row">
                <div>
                  <label for="duration-days">Days</label>
                  <input id="duration-days" v-model.number="durationDays" min="1" max="7" type="number" />
                </div>
                <div>
                  <label for="transportation-mode">Mode</label>
                  <select id="transportation-mode" v-model="transportationMode">
                    <option value="walking">Walking</option>
                    <option value="public_transport">Public transportation</option>
                    <option value="car_taxi">Car/taxi</option>
                  </select>
                </div>
              </div>

              <button class="button compact-button" type="submit" :disabled="chatStore.isRefining">
                Refine Itinerary
              </button>
            </form>

            <div v-if="chatStore.lastRefinement" class="source-note-panel">
              <h2>{{ chatStore.lastRefinement.itinerary.title }}</h2>
              <p>{{ chatStore.lastRefinement.itinerary.summary }}</p>
              <p class="muted">Private subscriber itinerary: {{ chatStore.lastRefinement.itinerary.id }}</p>
            </div>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import type { TransportationMode } from "../types";
import { useAuthStore } from "../stores/authStore";
import { useSubscriberChatStore } from "../stores/subscriberChatStore";

const authStore = useAuthStore();
const chatStore = useSubscriberChatStore();

const messageText = ref("");
const sourceItineraryId = ref("it-london-oliver-twist-1-walking");
const refinementPrompt = ref("Make this route slower and more reflective.");
const durationDays = ref(1);
const transportationMode = ref<TransportationMode>("walking");

onMounted(() => {
  if (authStore.isSubscriber) {
    void chatStore.loadSessions();
  }
});

watch(
  () => authStore.isSubscriber,
  (isSubscriber) => {
    if (isSubscriber) {
      void chatStore.loadSessions();
    } else {
      chatStore.reset();
    }
  },
);

function startSession(): void {
  void chatStore.startSession("Subscriber itinerary chat");
}

function sendMessage(): void {
  const content = messageText.value.trim();
  if (!content) {
    return;
  }
  void chatStore.sendMessage(content).then((sent) => {
    if (sent) {
      messageText.value = "";
    }
  });
}

function refineItinerary(): void {
  void chatStore.refineItinerary({
    sourceItineraryId: sourceItineraryId.value,
    prompt: refinementPrompt.value,
    durationDays: durationDays.value,
    transportationMode: transportationMode.value,
  });
}
</script>

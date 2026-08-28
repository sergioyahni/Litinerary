import { createApp } from "vue";
import { createPinia } from "pinia";
import { createAuth0 } from "@auth0/auth0-vue";
import App from "./App.vue";
import router from "./router";
import {
  AUTH_RUNTIME_CONFIG,
  auth0ConfigurationErrors,
  usesAuth0,
} from "./services/authService";
import "./assets/main.css";

const app = createApp(App);

app.use(createPinia());
app.use(router);

if (usesAuth0() && auth0ConfigurationErrors().length === 0) {
  app.use(
    createAuth0(
      {
        domain: AUTH_RUNTIME_CONFIG.auth0Domain,
        clientId: AUTH_RUNTIME_CONFIG.auth0ClientId,
        cacheLocation: AUTH_RUNTIME_CONFIG.auth0CacheLocation,
        useRefreshTokens: AUTH_RUNTIME_CONFIG.auth0UseRefreshTokens,
        authorizationParams: {
          audience: AUTH_RUNTIME_CONFIG.auth0Audience,
          redirect_uri: AUTH_RUNTIME_CONFIG.auth0CallbackUrl,
        },
      },
      {
        errorPath: "/auth/callback",
      },
    ),
  );
}

app.mount("#app");

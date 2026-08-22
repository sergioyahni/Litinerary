const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? DEFAULT_API_BASE_URL;

type AuthTokenProvider = () => string | null | Promise<string | null>;

let authTokenProvider: AuthTokenProvider | null = null;

export function setAuthTokenProvider(provider: AuthTokenProvider | null): void {
  authTokenProvider = provider;
}

export class ApiError extends Error {
  status: number;
  detail: string;
  isUnauthorized: boolean;
  isForbidden: boolean;
  isRateLimited: boolean;
  retryAfterSeconds: number | null;

  constructor(status: number, detail: string, retryAfterSeconds: number | null = null) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.isUnauthorized = status === 401;
    this.isForbidden = status === 403;
    this.isRateLimited = status === 429;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = (await authTokenProvider?.()) ?? null;
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    ...options,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (
        payload.detail &&
        typeof payload.detail === "object" &&
        "message" in payload.detail &&
        typeof payload.detail.message === "string"
      ) {
        detail = payload.detail.message;
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(response.status, detail, retryAfterSeconds(response.headers));
  }

  return response.json() as Promise<T>;
}

function retryAfterSeconds(headers: Headers | undefined): number | null {
  const value = headers?.get("Retry-After");
  if (!value) {
    return null;
  }
  const seconds = Number(value);
  if (Number.isFinite(seconds) && seconds >= 0) {
    return seconds;
  }
  const retryAt = Date.parse(value);
  if (Number.isNaN(retryAt)) {
    return null;
  }
  return Math.max(0, Math.ceil((retryAt - Date.now()) / 1000));
}

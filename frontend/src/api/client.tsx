import {
  parseError,
  formatErrorForLogging,
  toParsedAppError,
  type ParsedAppError,
} from "../utils/errorHandler";
import {
  clearStoredAuthTokens,
  updateStoredAccessToken,
} from "../auth/authStorage";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

// Cross-tab synchronized flag using localStorage
const REFRESH_LOCK_KEY = "token_refresh_in_progress";
const REFRESH_LOCK_TIMEOUT = 10000; // 10 seconds max lock duration

/**
 * Try to acquire cross-tab refresh lock using localStorage.
 * Returns true if lock acquired, false if another tab is refreshing.
 */
function tryAcquireRefreshLock(): boolean {
  const now = Date.now();
  const existing = localStorage.getItem(REFRESH_LOCK_KEY);

  if (existing) {
    const lockTime = parseInt(existing, 10);
    // Validate parseInt succeeded before arithmetic operations
    if (isNaN(lockTime)) {
      // Invalid lock value, steal it
      localStorage.setItem(REFRESH_LOCK_KEY, now.toString());
      return true;
    }
    // If lock is stale (> 10s old), steal it
    if (now - lockTime > REFRESH_LOCK_TIMEOUT) {
      localStorage.setItem(REFRESH_LOCK_KEY, now.toString());
      return true;
    }
    return false; // Another tab is refreshing
  }

  // No lock exists, acquire it
  localStorage.setItem(REFRESH_LOCK_KEY, now.toString());
  return true;
}

/**
 * Release the cross-tab refresh lock.
 */
function releaseRefreshLock(): void {
  localStorage.removeItem(REFRESH_LOCK_KEY);
}

/**
 * Check if a refresh is in progress (in any tab).
 */
function isRefreshInProgress(): boolean {
  const existing = localStorage.getItem(REFRESH_LOCK_KEY);
  if (!existing) return false;

  const lockTime = parseInt(existing, 10);
  // Validate parseInt succeeded before arithmetic operations
  if (isNaN(lockTime)) {
    // Invalid lock value, consider it not in progress
    return false;
  }
  const now = Date.now();

  // Consider stale if > 10s old
  return (now - lockTime) <= REFRESH_LOCK_TIMEOUT;
}

function toHeaderRecord(headers?: HeadersInit): Record<string, string> {
  if (!headers) {
    return {};
  }

  if (headers instanceof Headers) {
    const record: Record<string, string> = {};
    headers.forEach((value, key) => {
      record[key] = value;
    });
    return record;
  }

  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }

  return { ...headers };
}

function buildRequestHeaders(
  options: RequestInit,
  token: string | null,
  includeJsonContentType: boolean,
): Record<string, string> {
  const headers: Record<string, string> = {
    ...toHeaderRecord(options.headers),
  };

  if (includeJsonContentType && !("Content-Type" in headers)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

async function parseSuccessResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

interface BackendErrorEnvelope {
  error?: unknown;
  detail?: unknown;
}

function extractBackendErrorPayload(payload: unknown): unknown {
  if (payload && typeof payload === "object") {
    const envelope = payload as BackendErrorEnvelope;
    return envelope.error ?? envelope.detail ?? payload;
  }

  return payload;
}

async function parseFailureResponse(
  response: Response,
  fallbackMessage: string,
): Promise<ParsedAppError> {
  try {
    const payload: unknown = await response.json();
    return toParsedAppError(
      extractBackendErrorPayload(payload),
      fallbackMessage,
    );
  } catch {
    return toParsedAppError(response, fallbackMessage);
  }
}

async function refreshToken(): Promise<string | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      clearStoredAuthTokens();
      return null;
    }

    const data = await response.json();
    const newToken = data.access_token;
    updateStoredAccessToken(newToken);
    return newToken;
  } catch (error) {
    // Network error or other issue
    return null;
  }
}

/**
 * Enhanced API fetch with unified error handling.
 *
 * All errors are parsed and formatted consistently using parseError().
 * Errors are logged to console with full details for debugging.
 *
 * @throws {Error} Always throws with structured error information
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  return apiRequest<T>(path, options, true);
}

export async function apiFetchFormData<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  return apiRequest<T>(path, options, false);
}

export async function apiFetchBlob(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const response = await apiRequest<Response>(path, options, true, true);
  return response;
}

async function apiRequest<T>(
  path: string,
  options: RequestInit,
  includeJsonContentType: boolean,
  returnRawResponse = false,
): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const headers = buildRequestHeaders(options, token, includeJsonContentType);

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (error) {
    // Network error (e.g., no internet, CORS, DNS failure)
    const parsedError = parseError(error, "Network request failed");
    console.error(formatErrorForLogging(parsedError));
    throw toParsedAppError(error, "Network request failed");
  }

  // Handle 401 Unauthorized - attempt token refresh
  if (res.status === 401 && token) {
    // Don't retry for auth endpoints (login, register, refresh, logout)
    if (path.startsWith("/auth/")) {
      const parsedAppError = await parseFailureResponse(
        res,
        "Authentication failed",
      );
      console.error(formatErrorForLogging(parsedAppError));
      throw parsedAppError;
    }

    // Try to acquire refresh lock (cross-tab synchronized)
    if (!tryAcquireRefreshLock()) {
      // Another tab is refreshing — wait for the lock to be released via StorageEvent.
      return new Promise((resolve, reject) => {
        let timeoutId: ReturnType<typeof setTimeout>;

        const cleanup = () => {
          clearTimeout(timeoutId);
          window.removeEventListener("storage", onStorage);
        };

        const retry = () => {
          cleanup();
          const newToken = localStorage.getItem("auth_token");
          if (!newToken) {
            reject(new Error("Session expired. Please login again."));
            return;
          }
          const newHeaders = {
            ...headers,
            Authorization: `Bearer ${newToken}`,
          };
          fetch(`${API_BASE_URL}${path}`, { ...options, headers: newHeaders, credentials: "include" })
            .then(async (retryRes) => {
              if (!retryRes.ok) {
                const parsedAppError = await parseFailureResponse(retryRes, "API request failed");
                console.error(formatErrorForLogging(parsedAppError));
                throw parsedAppError;
              }
              return returnRawResponse ? (retryRes as T) : parseSuccessResponse<T>(retryRes);
            })
            .then(resolve)
            .catch(reject);
        };

        const onStorage = (event: StorageEvent) => {
          // The lock is released when the key is removed from localStorage.
          if (event.key === REFRESH_LOCK_KEY && event.newValue === null) {
            retry();
          }
        };

        window.addEventListener("storage", onStorage);

        timeoutId = setTimeout(() => {
          cleanup();
          reject(new Error("Token refresh timeout"));
        }, 15000);
      });
    }

    // We acquired the lock, perform the refresh
    let newToken: string | null = null;
    try {
      newToken = await refreshToken();
    } finally {
      releaseRefreshLock();
    }

    if (!newToken) {
      // Refresh failed — clear tokens and redirect to login, but only when not
      // already on the login/account page to avoid a redirect loop.
      clearStoredAuthTokens();
      if (!window.location.pathname.startsWith("/account")) {
        window.location.href = "/account";
      }
      throw new Error("Session expired. Please login again.");
    }

    // Retry the original request with new token
    const newHeaders = {
      ...headers,
      Authorization: `Bearer ${newToken}`,
    };

    const retryRes = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: newHeaders,
      credentials: "include",
    });

    if (!retryRes.ok) {
      const parsedAppError = await parseFailureResponse(
        retryRes,
        "API request failed",
      );
      console.error(formatErrorForLogging(parsedAppError));
      throw parsedAppError;
    }

    return returnRawResponse ? (retryRes as T) : parseSuccessResponse<T>(retryRes);
  }

  // Handle non-401 errors
  if (!res.ok) {
    const parsedAppError = await parseFailureResponse(
      res,
      "API request failed",
    );
    console.error(formatErrorForLogging(parsedAppError));
    throw parsedAppError;
  }

  return returnRawResponse ? (res as T) : parseSuccessResponse<T>(res);
}

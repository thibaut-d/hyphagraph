import {
  parseError,
  formatErrorForLogging,
  toParsedAppError,
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

async function parseSuccessResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

async function refreshToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearStoredAuthTokens();
      return null;
    }

    const data = await response.json();
    const newToken = data.access_token;

    // Update stored token
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
  const token = localStorage.getItem("auth_token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...toHeaderRecord(options.headers),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
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
      let errorData: any;
      try {
        errorData = await res.json();
      } catch {
        const parsedAppError = toParsedAppError(res, "Authentication failed");
        console.error(formatErrorForLogging(parsedAppError));
        throw parsedAppError;
      }

      // Parse backend error response
      const backendError = errorData.error || errorData.detail || errorData;
      const parsedAppError = toParsedAppError(backendError, "Authentication failed");
      console.error(formatErrorForLogging(parsedAppError));
      throw parsedAppError;
    }

    // Try to acquire refresh lock (cross-tab synchronized)
    if (!tryAcquireRefreshLock()) {
      // Another tab is refreshing, wait for it to complete
      return new Promise((resolve, reject) => {
        const cleanup = (timeoutId: ReturnType<typeof setTimeout>) => {
          clearInterval(checkRefresh);
          clearTimeout(timeoutId);
        };

        const checkRefresh = setInterval(() => {
          if (!isRefreshInProgress()) {
            cleanup(timeoutId);

            // Refresh completed in another tab, retry with new token
            const newToken = localStorage.getItem("auth_token");
            if (!newToken) {
              reject(new Error("Session expired. Please login again."));
              return;
            }

            const newHeaders = {
              ...headers,
              Authorization: `Bearer ${newToken}`,
            };

            fetch(`${API_BASE_URL}${path}`, {
              ...options,
              headers: newHeaders,
            })
              .then(async (retryRes) => {
                if (!retryRes.ok) {
                  let errorData: any;
                  try {
                    errorData = await retryRes.json();
                  } catch {
                    const parsedAppError = toParsedAppError(retryRes, "API request failed");
                    console.error(formatErrorForLogging(parsedAppError));
                    throw parsedAppError;
                  }

                  const backendError = errorData.error || errorData.detail || errorData;
                  const parsedAppError = toParsedAppError(backendError, "API request failed");
                  console.error(formatErrorForLogging(parsedAppError));
                  throw parsedAppError;
                }
                return parseSuccessResponse<T>(retryRes);
              })
              .then(resolve)
              .catch(reject);
          }
        }, 100); // Check every 100ms

        // Timeout after 15 seconds
        const timeoutId = setTimeout(() => {
          clearInterval(checkRefresh);
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
      // Refresh failed, redirect to login
      clearStoredAuthTokens();
      window.location.href = "/account";
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
    });

    if (!retryRes.ok) {
      let errorData: any;
      try {
        errorData = await retryRes.json();
      } catch {
        const parsedAppError = toParsedAppError(retryRes, "API request failed");
        console.error(formatErrorForLogging(parsedAppError));
        throw parsedAppError;
      }

      const backendError = errorData.error || errorData.detail || errorData;
      const parsedAppError = toParsedAppError(backendError, "API request failed");
      console.error(formatErrorForLogging(parsedAppError));
      throw parsedAppError;
    }

    return parseSuccessResponse<T>(retryRes);
  }

  // Handle non-401 errors
  if (!res.ok) {
    let errorData: any;
    try {
      errorData = await res.json();
    } catch {
      const parsedAppError = toParsedAppError(res, "API request failed");
      console.error(formatErrorForLogging(parsedAppError));
      throw parsedAppError;
    }

    // Backend sends errors in { error: { code, message, details, ... } } format
    const backendError = errorData.error || errorData.detail || errorData;
    const parsedAppError = toParsedAppError(backendError, "API request failed");
    console.error(formatErrorForLogging(parsedAppError));
    throw parsedAppError;
  }

  return parseSuccessResponse<T>(res);
}

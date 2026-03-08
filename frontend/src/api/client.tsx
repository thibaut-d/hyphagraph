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
      // Refresh token is invalid or expired, clear auth
      localStorage.removeItem("auth_token");
      localStorage.removeItem("refresh_token");
      return null;
    }

    const data = await response.json();
    const newToken = data.access_token;

    // Update stored token
    localStorage.setItem("auth_token", newToken);

    return newToken;
  } catch (error) {
    // Network error or other issue
    return null;
  }
}

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

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized - attempt token refresh
  if (res.status === 401 && token) {
    // Don't retry for auth endpoints (login, register, refresh, logout)
    if (path.startsWith("/auth/")) {
      let error: any;
      try {
        error = await res.json();
      } catch {
        throw new Error("API error");
      }
      const detail = error.detail;
      if (typeof detail === 'string') {
        throw new Error(detail);
      } else if (typeof detail === 'object' && detail !== null) {
        throw new Error(JSON.stringify(detail));
      }
      throw new Error("API error");
    }

    // Try to acquire refresh lock (cross-tab synchronized)
    if (!tryAcquireRefreshLock()) {
      // Another tab is refreshing, wait for it to complete
      return new Promise((resolve, reject) => {
        const checkRefresh = setInterval(() => {
          if (!isRefreshInProgress()) {
            clearInterval(checkRefresh);

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
                  let error: any;
                  try {
                    error = await retryRes.json();
                  } catch {
                    throw new Error("API error");
                  }
                  const detail = error.detail;
                  if (typeof detail === 'string') {
                    throw new Error(detail);
                  } else if (typeof detail === 'object' && detail !== null) {
                    throw new Error(JSON.stringify(detail));
                  }
                  throw new Error("API error");
                }
                return retryRes.json();
              })
              .then(resolve)
              .catch(reject);
          }
        }, 100); // Check every 100ms

        // Timeout after 15 seconds
        setTimeout(() => {
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
      let error: any;
      try {
        error = await retryRes.json();
      } catch {
        throw new Error("API error");
      }
      const detail = error.detail;
      if (typeof detail === 'string') {
        throw new Error(detail);
      } else if (typeof detail === 'object' && detail !== null) {
        throw new Error(JSON.stringify(detail));
      }
      throw new Error("API error");
    }

    return retryRes.json();
  }

  if (!res.ok) {
    let error: any;
    try {
      error = await res.json();
    } catch {
      throw new Error("API error");
    }
    // Handle error.detail which might be a string or object
    const detail = error.detail;
    if (typeof detail === 'string') {
      throw new Error(detail);
    } else if (typeof detail === 'object' && detail !== null) {
      // For validation errors or structured errors, stringify it
      throw new Error(JSON.stringify(detail));
    }
    throw new Error("API error");
  }

  // Handle 204 No Content responses (e.g., password reset requests)
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

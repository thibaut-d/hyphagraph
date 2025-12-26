const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// Flag to prevent concurrent token refresh requests
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function subscribeTokenRefresh(callback: (token: string) => void) {
  refreshSubscribers.push(callback);
}

function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
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

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
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
      throw new Error(error.detail ?? "API error");
    }

    // Handle concurrent requests with single refresh
    if (isRefreshing) {
      // Wait for the ongoing refresh to complete
      return new Promise((resolve, reject) => {
        subscribeTokenRefresh((newToken: string) => {
          // Retry original request with new token
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
                throw new Error(error.detail ?? "API error");
              }
              return retryRes.json();
            })
            .then(resolve)
            .catch(reject);
        });
      });
    }

    // Attempt to refresh the token
    isRefreshing = true;
    const newToken = await refreshToken();
    isRefreshing = false;

    if (!newToken) {
      // Refresh failed, redirect to login
      window.location.href = "/account";
      throw new Error("Session expired. Please login again.");
    }

    // Notify all waiting requests
    onTokenRefreshed(newToken);

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
      throw new Error(error.detail ?? "API error");
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
    throw new Error(error.detail ?? "API error");
  }

  return res.json();
}
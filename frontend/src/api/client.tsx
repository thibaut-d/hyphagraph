import {
  parseError,
  formatErrorForLogging,
  toParsedAppError,
  type ParsedAppError,
} from "../utils/errorHandler";
import {
  clearStoredAuthTokens,
  getStoredAuthTokens,
  updateStoredAccessToken,
} from "../auth/authStorage";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

// In-memory coalescing lock: all concurrent 401s within this tab share one refresh request.
let _refreshPromise: Promise<string | null> | null = null;

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
}

function extractBackendErrorPayload(payload: unknown): unknown {
  if (payload && typeof payload === "object") {
    const envelope = payload as BackendErrorEnvelope;
    return envelope.error ?? payload;
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
  } catch {
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
  const token = getStoredAuthTokens().token;
  const headers = buildRequestHeaders(options, token, includeJsonContentType);

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (error) {
    // Abort is an expected cancellation path — re-throw without logging or wrapping.
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
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

    // Coalesce concurrent 401s: all share one refresh network request.
    if (!_refreshPromise) {
      _refreshPromise = refreshToken().finally(() => {
        _refreshPromise = null;
      });
    }
    const newToken = await _refreshPromise;

    if (!newToken) {
      // Refresh failed — redirect to login unless already there.
      if (!window.location.pathname.startsWith("/account")) {
        window.location.href = "/account";
      }
      throw new Error("Session expired. Please login again.");
    }

    // Retry the original request with the refreshed token.
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

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "./client";
import { ErrorCode, ParsedAppError } from "../utils/errorHandler";

const REFRESH_LOCK_KEY = "token_refresh_in_progress";

function createResponse(
  status: number,
  options: {
    json?: ReturnType<typeof vi.fn>;
    statusText?: string;
  } = {},
): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: options.statusText ?? "",
    json: options.json ?? vi.fn().mockResolvedValue({}),
  } as unknown as Response;
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}

describe("apiFetch", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns undefined for 204 responses after a local token refresh", async () => {
    localStorage.setItem("auth_token", "stale-token");

    const retryJson = vi.fn();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createResponse(401))
      .mockResolvedValueOnce(
        createResponse(200, {
          json: vi.fn().mockResolvedValue({ access_token: "new-token" }),
        }),
      )
      .mockResolvedValueOnce(createResponse(204, { json: retryJson }));

    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch<void>("/sources/123", { method: "DELETE" })).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(retryJson).not.toHaveBeenCalled();
  });

  it("returns undefined for 204 responses after waiting on another tab to refresh", async () => {
    vi.useFakeTimers();

    localStorage.setItem("auth_token", "stale-token");
    localStorage.setItem(REFRESH_LOCK_KEY, Date.now().toString());

    const retryJson = vi.fn();
    const initialRequest = createDeferred<Response>();
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => initialRequest.promise)
      .mockResolvedValueOnce(createResponse(204, { json: retryJson }));

    vi.stubGlobal("fetch", fetchMock);

    const requestPromise = apiFetch<void>("/sources/123", { method: "DELETE" });

    initialRequest.resolve(createResponse(401));
    await Promise.resolve();

    localStorage.setItem("auth_token", "new-token");
    localStorage.removeItem(REFRESH_LOCK_KEY);
    // jsdom 27 doesn't fire storage events for same-window modifications (per spec);
    // dispatch manually to simulate the other tab releasing the lock.
    window.dispatchEvent(
      new StorageEvent("storage", { key: REFRESH_LOCK_KEY, newValue: null }),
    );

    await vi.advanceTimersByTimeAsync(100);

    await expect(requestPromise).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(retryJson).not.toHaveBeenCalled();
  });

  it("preserves structured backend errors for UI consumers", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      createResponse(404, {
        json: vi.fn().mockResolvedValue({
          error: {
            code: ErrorCode.ENTITY_NOT_FOUND,
            message: "Entity not found",
            details: "Entity with ID '123' does not exist",
            context: { entity_id: "123" },
          },
        }),
      }),
    );

    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch("/entities/123")).rejects.toMatchObject({
      name: "ParsedAppError",
      message: "Entity not found",
      userMessage: "Entity not found",
      developerMessage: "Entity with ID '123' does not exist",
      code: ErrorCode.ENTITY_NOT_FOUND,
      context: { entity_id: "123" },
    } satisfies Partial<ParsedAppError>);
  });

  it("falls back to response metadata when the backend error body is not JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      createResponse(503, {
        statusText: "Service Unavailable",
        json: vi.fn().mockRejectedValue(new SyntaxError("Unexpected token <")),
      }),
    );

    vi.stubGlobal("fetch", fetchMock);

    await expect(apiFetch("/search?q=aspirin")).rejects.toMatchObject({
      name: "ParsedAppError",
      message: "Server error. Please try again later.",
      userMessage: "Server error. Please try again later.",
      developerMessage: "HTTP 503: Service Unavailable",
      code: ErrorCode.INTERNAL_SERVER_ERROR,
      statusCode: 503,
    } satisfies Partial<ParsedAppError>);
  });
});

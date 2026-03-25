import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "./client";
import { setStoredAuthTokens, clearStoredAuthTokens } from "../auth/authStorage";
import { ErrorCode, ParsedAppError } from "../utils/errorHandler";

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
    clearStoredAuthTokens();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
    clearStoredAuthTokens();
  });

  it("returns undefined for 204 responses after a local token refresh", async () => {
    setStoredAuthTokens("stale-token");

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

  it("concurrent 401s within one tab share a single refresh request", async () => {
    setStoredAuthTokens("stale-token");

    const retryJson = vi.fn().mockResolvedValue({});
    const refreshDeferred = createDeferred<Response>();

    // Both parallel requests initially get 401. Then the shared refresh request
    // resolves and both are retried.
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(createResponse(401))           // request 1 → 401
      .mockResolvedValueOnce(createResponse(401))           // request 2 → 401
      .mockImplementationOnce(() => refreshDeferred.promise) // shared refresh
      .mockResolvedValue(createResponse(204, { json: retryJson })); // both retries

    vi.stubGlobal("fetch", fetchMock);

    const p1 = apiFetch<void>("/sources/1", { method: "DELETE" });
    const p2 = apiFetch<void>("/sources/2", { method: "DELETE" });

    // Let both 401s land, then resolve the shared refresh.
    await Promise.resolve();
    refreshDeferred.resolve(
      createResponse(200, {
        json: vi.fn().mockResolvedValue({ access_token: "new-token" }),
      }),
    );

    await expect(p1).resolves.toBeUndefined();
    await expect(p2).resolves.toBeUndefined();

    // Exactly one refresh call should have been made.
    const refreshCalls = fetchMock.mock.calls.filter((call) =>
      (call[0] as string).includes("/auth/refresh"),
    );
    expect(refreshCalls).toHaveLength(1);
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

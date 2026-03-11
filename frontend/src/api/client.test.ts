import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "./client";

const REFRESH_LOCK_KEY = "token_refresh_in_progress";

function createResponse(
  status: number,
  options: {
    json?: ReturnType<typeof vi.fn>;
  } = {},
): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
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
    localStorage.setItem("refresh_token", "refresh-token");

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
    localStorage.setItem("refresh_token", "refresh-token");
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

    await vi.advanceTimersByTimeAsync(100);

    await expect(requestPromise).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(retryJson).not.toHaveBeenCalled();
  });
});

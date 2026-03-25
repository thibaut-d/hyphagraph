import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuthContext } from "./AuthContext";
import { updateStoredAccessToken } from "./authStorage";

vi.mock("../api/auth", () => ({
  getMe: vi.fn(),
  logout: vi.fn(),
  refreshAccessToken: vi.fn(),
}));

import { getMe, logout, refreshAccessToken } from "../api/auth";

function AuthConsumer() {
  const { token, user, logout: logoutUser } = useAuthContext();

  return (
    <>
      <div>{`token:${token ?? "none"}`}</div>
      <div>{`user:${user?.email ?? "none"}`}</div>
      <button onClick={logoutUser} type="button">
        Logout
      </button>
    </>
  );
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

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("syncs token changes without polling when the access token changes in the same tab", async () => {
    // Session restore returns "stale-token" from the refresh cookie.
    vi.mocked(refreshAccessToken).mockResolvedValue({
      access_token: "stale-token",
      token_type: "bearer",
    });

    vi.mocked(getMe)
      .mockResolvedValueOnce({
        id: "1",
        email: "stale@example.com",
        is_active: true,
        is_superuser: false,
        is_verified: true,
        created_at: "2026-03-11T00:00:00Z",
      })
      .mockResolvedValueOnce({
        id: "1",
        email: "fresh@example.com",
        is_active: true,
        is_superuser: false,
        is_verified: true,
        created_at: "2026-03-11T00:00:00Z",
      });

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>,
    );

    await screen.findByText("user:stale@example.com");

    await act(async () => {
      updateStoredAccessToken("fresh-token");
    });

    await waitFor(() => {
      expect(screen.getByText("token:fresh-token")).toBeInTheDocument();
    });
    await screen.findByText("user:fresh@example.com");
  });

  it("ignores stale getMe responses that resolve after logout", async () => {
    // Session restore returns "active-token" from the refresh cookie.
    vi.mocked(refreshAccessToken).mockResolvedValue({
      access_token: "active-token",
      token_type: "bearer",
    });

    const pendingUserRequest = createDeferred<{
      id: string;
      email: string;
      is_active: boolean;
      is_superuser: boolean;
      is_verified: boolean;
      created_at: string;
    }>();

    vi.mocked(getMe).mockReturnValueOnce(pendingUserRequest.promise);
    vi.mocked(logout).mockResolvedValue(undefined);

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>,
    );

    // Wait for session restore to complete and the token to be visible before
    // triggering logout — this ensures getMe has been called with the token.
    await screen.findByText("token:active-token");

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(screen.getByText("token:none")).toBeInTheDocument();
      expect(screen.getByText("user:none")).toBeInTheDocument();
    });

    // Late-resolving getMe must NOT update the user after logout.
    pendingUserRequest.resolve({
      id: "1",
      email: "late@example.com",
      is_active: true,
      is_superuser: false,
      is_verified: true,
      created_at: "2026-03-11T00:00:00Z",
    });

    await waitFor(() => {
      expect(screen.getByText("user:none")).toBeInTheDocument();
    });
  });
});

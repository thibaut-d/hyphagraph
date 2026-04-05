/**
 * Tests for ProtectedRoute component.
 *
 * Tests loading state, authentication redirection, and protected content rendering.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { ProtectedRoute } from "../ProtectedRoute";
import { SuperuserRoute } from "../SuperuserRoute";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (_key: string, defaultValue?: string) => defaultValue ?? _key,
  }),
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

// Mock useAuth hook
const mockUseAuth = vi.fn();
vi.mock("../../auth/useAuth", () => ({
  useAuth: () => mockUseAuth(),
}));

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading spinner when auth is loading", () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true });

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    );

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("redirects to /account when not authenticated", () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false });

    render(
      <MemoryRouter initialEntries={["/protected"]}>
        <Routes>
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
          <Route path="/account" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("passes the attempted path as returnTo state when redirecting", () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false });

    // Capture the location state on the /account route
    let capturedState: unknown = undefined;
    function AccountCapture() {
      const loc = useLocation();
      capturedState = loc.state;
      return <div>Login Page</div>;
    }

    render(
      <MemoryRouter initialEntries={["/entities/abc/edit"]}>
        <Routes>
          <Route
            path="/entities/:id/edit"
            element={
              <ProtectedRoute>
                <div>Edit Page</div>
              </ProtectedRoute>
            }
          />
          <Route path="/account" element={<AccountCapture />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(capturedState).toEqual({ returnTo: "/entities/abc/edit" });
  });

  it("renders children when authenticated", () => {
    const mockUser = { id: "user-123", email: "test@example.com" };
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false });

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    );

    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });

  it("handles transition from loading to authenticated", async () => {
    const mockUser = { id: "user-123", email: "test@example.com" };

    // Start with loading
    mockUseAuth.mockReturnValue({ user: null, loading: true });

    const { rerender } = render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    );

    expect(screen.getByRole("progressbar")).toBeInTheDocument();

    // Transition to authenticated
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false });
    rerender(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  it("renders complex children when authenticated", () => {
    const mockUser = { id: "user-123", email: "test@example.com" };
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false });

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>
            <h1>Dashboard</h1>
            <p>Welcome back!</p>
          </div>
        </ProtectedRoute>
      </MemoryRouter>
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Welcome back!")).toBeInTheDocument();
  });
});

describe("SuperuserRoute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a forbidden state for authenticated non-superusers", () => {
    mockUseAuth.mockReturnValue({
      user: { id: "user-123", email: "test@example.com", is_superuser: false },
      loading: false,
    });

    render(
      <MemoryRouter initialEntries={["/review-queue"]}>
        <Routes>
          <Route
            path="/review-queue"
            element={
              <SuperuserRoute>
                <div>Review Queue</div>
              </SuperuserRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("403 Forbidden")).toBeInTheDocument();
    expect(screen.getByText("You do not have permission to access this page.")).toBeInTheDocument();
    expect(screen.queryByText("Review Queue")).not.toBeInTheDocument();
  });

  it("renders children for superusers", () => {
    mockUseAuth.mockReturnValue({
      user: { id: "admin-123", email: "admin@example.com", is_superuser: true },
      loading: false,
    });

    render(
      <MemoryRouter>
        <SuperuserRoute>
          <div>Review Queue</div>
        </SuperuserRoute>
      </MemoryRouter>
    );

    expect(screen.getByText("Review Queue")).toBeInTheDocument();
  });
});

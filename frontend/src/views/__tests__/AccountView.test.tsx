import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import { AccountView } from "../AccountView";
import * as authApi from "../../api/auth";
import { NotificationProvider } from "../../notifications/NotificationContext";

const mockLogin = vi.fn();
const mockLogout = vi.fn();

vi.mock("../../api/auth");

vi.mock("../../auth/useAuth", () => ({
  useAuth: () => ({
    user: null,
    login: mockLogin,
    logout: mockLogout,
  }),
}));

function renderView(
  initialEntry: string | { pathname: string; state?: unknown } = "/account",
) {
  return render(
    <NotificationProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/account" element={<AccountView />} />
          <Route path="/sources/new" element={<div>Protected destination</div>} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  );
}

describe("AccountView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "token-123",
      token_type: "bearer",
    });
    vi.mocked(authApi.register).mockResolvedValue({
      message: "registered",
    } as any);
  });

  it("redirects to the requested destination after login", async () => {
    const user = userEvent.setup();
    renderView({ pathname: "/account", state: { returnTo: "/sources/new" } });

    await user.type(screen.getByRole("textbox", { name: /email/i }), "user@example.com");
    await user.type(screen.getAllByLabelText(/password/i)[0], "password123");
    await user.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("token-123");
      expect(screen.getByText("Protected destination")).toBeInTheDocument();
    });
  });

  it("submits registration when Enter is pressed from the registration flow", async () => {
    const user = userEvent.setup();
    render(
      <NotificationProvider>
        <MemoryRouter
          initialEntries={[{ pathname: "/account", state: { returnTo: "/sources/new" } }]}
        >
          <Routes>
            <Route path="/account" element={<AccountView />} />
            <Route path="/sources/new" element={<div>Protected destination</div>} />
          </Routes>
        </MemoryRouter>
      </NotificationProvider>,
    );

    await user.type(screen.getByRole("textbox", { name: /email/i }), "new@example.com");
    await user.type(screen.getAllByLabelText(/password/i)[0], "password123");
    await user.type(screen.getByLabelText(/confirm password/i), "password123");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(authApi.register).toHaveBeenCalledWith({
        email: "new@example.com",
        password: "password123",
        password_confirmation: "password123",
      });
    });

    expect(authApi.login).not.toHaveBeenCalled();
  });
});

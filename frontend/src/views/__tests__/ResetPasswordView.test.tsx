import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";

import ResetPasswordView from "../ResetPasswordView";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
  initReactI18next: { type: "3rdParty", init: vi.fn() },
}));

vi.mock("../../i18n", () => ({
  default: { t: (key: string) => key },
}));

vi.mock("../../api/auth");

vi.mock("../../notifications/NotificationContext", () => ({
  NotificationProvider: ({ children }: { children: ReactNode }) => children,
  useNotification: () => ({
    showError: vi.fn(),
    showSuccess: vi.fn(),
    showWarning: vi.fn(),
    showInfo: vi.fn(),
  }),
}));

function renderWithToken(token: string | null = "test-token") {
  const search = token ? `?token=${token}` : "";
  return render(
    <MemoryRouter initialEntries={[`/reset-password${search}`]}>
      <ResetPasswordView />
    </MemoryRouter>,
  );
}

describe("ResetPasswordView — i18n", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page title via t()", () => {
    renderWithToken();
    expect(screen.getByText("reset_password.title")).toBeInTheDocument();
  });

  it("renders the subtitle via t()", () => {
    renderWithToken();
    expect(screen.getByText("reset_password.subtitle")).toBeInTheDocument();
  });

  it("renders the new password label via t()", () => {
    renderWithToken();
    expect(screen.getByText("change_password.new_password")).toBeInTheDocument();
  });

  it("renders the confirm password label via t()", () => {
    renderWithToken();
    expect(screen.getByText("change_password.confirm_password")).toBeInTheDocument();
  });

  it("renders the submit button via t()", () => {
    renderWithToken();
    expect(screen.getByRole("button", { name: "reset_password.submit" })).toBeInTheDocument();
  });

  it("renders the back-to-login link via t()", () => {
    renderWithToken();
    expect(screen.getByText("reset_password.back_to_login")).toBeInTheDocument();
  });

  it("renders the new password placeholder via t()", () => {
    renderWithToken();
    const input = screen.getByPlaceholderText("reset_password.new_password_placeholder");
    expect(input).toBeInTheDocument();
  });

  it("renders the confirm password placeholder via t()", () => {
    renderWithToken();
    const input = screen.getByPlaceholderText("reset_password.confirm_password_placeholder");
    expect(input).toBeInTheDocument();
  });
});

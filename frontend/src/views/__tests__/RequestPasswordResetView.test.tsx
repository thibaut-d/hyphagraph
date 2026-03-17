import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";

import RequestPasswordResetView from "../RequestPasswordResetView";

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

function renderView() {
  return render(
    <MemoryRouter initialEntries={["/forgot-password"]}>
      <RequestPasswordResetView />
    </MemoryRouter>,
  );
}

describe("RequestPasswordResetView — i18n", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page title via t()", () => {
    renderView();
    expect(screen.getByText("forgot_password.title")).toBeInTheDocument();
  });

  it("renders the subtitle via t()", () => {
    renderView();
    expect(screen.getByText("forgot_password.subtitle")).toBeInTheDocument();
  });

  it("renders the email label via t()", () => {
    renderView();
    expect(screen.getByText("forgot_password.email_label")).toBeInTheDocument();
  });

  it("renders the email placeholder via t()", () => {
    renderView();
    const input = screen.getByPlaceholderText("forgot_password.email_placeholder");
    expect(input).toBeInTheDocument();
  });

  it("renders the submit button via t()", () => {
    renderView();
    expect(screen.getByRole("button", { name: "forgot_password.submit" })).toBeInTheDocument();
  });

  it("renders the back-to-login link via t()", () => {
    renderView();
    expect(screen.getByText("forgot_password.back_to_login")).toBeInTheDocument();
  });
});

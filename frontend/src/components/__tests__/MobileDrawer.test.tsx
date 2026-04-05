import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { MobileDrawer } from "../layout/MobileDrawer";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback || _key,
  }),
}));

vi.mock("i18next", () => ({
  default: {
    language: "en",
  },
}));

vi.mock("../layout/LanguageSwitch", () => ({
  LanguageSwitch: () => <div>Language Switch</div>,
}));

describe("MobileDrawer", () => {
  it("shows signed-in user profile info in the drawer footer", () => {
    render(
      <MemoryRouter>
        <MobileDrawer
          open
          onClose={vi.fn()}
          menuItems={[]}
          categories={[]}
          user={{
            id: "user-1",
            email: "user@example.com",
            is_superuser: false,
            is_active: true,
            is_verified: true,
          } as any}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("user@example.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "My Profile" })).toHaveAttribute("href", "/profile");
    expect(screen.getByText("Language Switch")).toBeInTheDocument();
  });
});

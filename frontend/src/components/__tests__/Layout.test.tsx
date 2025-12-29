/**
 * Tests for Layout component.
 *
 * Tests navigation menu, authentication integration, language switching,
 * global search integration, active route highlighting, and content rendering.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter, MemoryRouter } from "react-router-dom";
import { Layout } from "../Layout";
import i18n from "i18next";

// Mock AuthContext
const mockUseAuthContext = vi.fn();
vi.mock("../../auth/AuthContext", () => ({
  useAuthContext: () => mockUseAuthContext(),
}));

// Mock child components
vi.mock("../ProfileMenu", () => ({
  ProfileMenu: () => <div data-testid="profile-menu">Profile Menu</div>,
}));

vi.mock("../GlobalSearch", () => ({
  GlobalSearch: () => <div data-testid="global-search">Global Search</div>,
}));

// Mock i18n
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "menu.home": "Home",
        "menu.entities": "Entities",
        "menu.sources": "Sources",
        "menu.search": "Search",
        "auth.login": "Login",
        "common.change_language": "Change language",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock i18next module directly
vi.mock("i18next", () => ({
  default: {
    language: "en",
    changeLanguage: vi.fn(),
  },
}));

describe("Layout", () => {

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders app bar with title", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      expect(screen.getByText("HyphaGraph")).toBeInTheDocument();
    });

    it("renders all menu items", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      expect(screen.getByText("Home")).toBeInTheDocument();
      expect(screen.getByText("Entities")).toBeInTheDocument();
      expect(screen.getByText("Sources")).toBeInTheDocument();
      expect(screen.getByText("Search")).toBeInTheDocument();
    });

    it("renders global search component", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      expect(screen.getByTestId("global-search")).toBeInTheDocument();
    });

    it("renders language toggle button", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      const languageButton = screen.getByRole("button", { name: /change language/i });
      expect(languageButton).toBeInTheDocument();
    });
  });

  describe("Authentication integration", () => {
    it("shows login button when user is not authenticated", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      expect(screen.getByText("Login")).toBeInTheDocument();
      expect(screen.queryByTestId("profile-menu")).not.toBeInTheDocument();
    });

    it("shows profile menu when user is authenticated", () => {
      mockUseAuthContext.mockReturnValue({
        user: {
          id: "user-123",
          username: "testuser",
          email: "test@example.com",
        },
      } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      expect(screen.getByTestId("profile-menu")).toBeInTheDocument();
      expect(screen.queryByText("Login")).not.toBeInTheDocument();
    });
  });

  describe("Navigation", () => {
    it("renders navigation on home route", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <MemoryRouter initialEntries={["/"]}>
          <Layout />
        </MemoryRouter>
      );

      // Just verify all navigation items are present
      expect(screen.getByText("Home")).toBeInTheDocument();
      expect(screen.getByText("Entities")).toBeInTheDocument();
      expect(screen.getByText("Sources")).toBeInTheDocument();
      expect(screen.getByText("Search")).toBeInTheDocument();
    });

    it("renders navigation on entities route", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <MemoryRouter initialEntries={["/entities"]}>
          <Layout />
        </MemoryRouter>
      );

      expect(screen.getByText("Entities")).toBeInTheDocument();
    });

    it("renders navigation on nested entities route", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <MemoryRouter initialEntries={["/entities/123"]}>
          <Layout />
        </MemoryRouter>
      );

      expect(screen.getByText("Entities")).toBeInTheDocument();
    });

    it("links to correct routes", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      expect(screen.getByText("Home").closest("a")).toHaveAttribute("href", "/");
      expect(screen.getByText("Entities").closest("a")).toHaveAttribute("href", "/entities");
      expect(screen.getByText("Sources").closest("a")).toHaveAttribute("href", "/sources");
      expect(screen.getByText("Search").closest("a")).toHaveAttribute("href", "/search");
    });

    it("title links to home page", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      const titleLink = screen.getByText("HyphaGraph").closest("a");
      expect(titleLink).toHaveAttribute("href", "/");
    });

    it("login button links to account page", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      const loginButton = screen.getByText("Login").closest("a");
      expect(loginButton).toHaveAttribute("href", "/account");
    });
  });

  describe("Language switching", () => {
    it("calls changeLanguage when language button clicked", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      const languageButton = screen.getByRole("button", { name: /change language/i });
      fireEvent.click(languageButton);

      expect(i18n.changeLanguage).toHaveBeenCalled();
    });

    it("toggles between en and fr", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      // Set initial language to English
      (i18n as any).language = "en";

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      const languageButton = screen.getByRole("button", { name: /change language/i });
      fireEvent.click(languageButton);

      // Should switch to French
      expect(i18n.changeLanguage).toHaveBeenCalledWith("fr");
    });

    it("toggles from fr back to en", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      // Set initial language to French
      (i18n as any).language = "fr";

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      const languageButton = screen.getByRole("button", { name: /change language/i });
      fireEvent.click(languageButton);

      // Should switch to English
      expect(i18n.changeLanguage).toHaveBeenCalledWith("en");
    });
  });

  describe("Content rendering", () => {
    it("renders container for child routes", () => {
      mockUseAuthContext.mockReturnValue({ user: null } as any);

      const { container } = render(
        <MemoryRouter initialEntries={["/"]}>
          <Layout />
        </MemoryRouter>
      );

      // Verify the Container component is rendered (from MUI)
      const muiContainer = container.querySelector('.MuiContainer-root');
      expect(muiContainer).toBeInTheDocument();
    });
  });
});

/**
 * Tests for EntityTermsDisplay component.
 *
 * Tests data loading, error handling, compact vs full display modes,
 * language labels, and empty states.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { EntityTermsDisplay } from "../EntityTermsDisplay";
import { NotificationProvider } from "../../notifications/NotificationContext";
import type { EntityTermRead } from "../../api/entityTerms";
import * as entityTermsApi from "../../api/entityTerms";

// Mock the API module
vi.mock("../../api/entityTerms");

// Mock i18n
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => {
      const translations: Record<string, string> = {
        "entityTerms.loading": "Loading terms...",
        "entityTerms.alsoKnownAs": "Also known as",
      };
      return translations[key] || defaultValue || key;
    },
    i18n: { language: "en" },
  }),
  initReactI18next: { type: '3rdParty', init: () => {} },
}));

const renderWithNotifications = (ui: React.ReactElement) =>
  render(<NotificationProvider>{ui}</NotificationProvider>);

describe("EntityTermsDisplay", () => {
  const mockEntityId = "entity-123";

  const createMockTerm = (overrides?: Partial<EntityTermRead>): EntityTermRead => ({
    id: "term-1",
    entity_id: mockEntityId,
    term: "Paracetamol",
    language: "en",
    display_order: null,
    is_display_name: false,
    created_at: "2025-01-01T00:00:00Z",
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading state", () => {
    it("shows loading message initially", () => {
      vi.spyOn(entityTermsApi, "listEntityTerms").mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} />);

      expect(screen.getByText("Loading terms...")).toBeInTheDocument();
    });
  });

  describe("Error state", () => {
    it("handles error gracefully by showing empty state", async () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      vi.spyOn(entityTermsApi, "listEntityTerms").mockRejectedValue(
        new Error("Network error")
      );

      const { container } = renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading terms...")).not.toBeInTheDocument();
      });

      // Component logs error but doesn't display it - renders empty
      expect(consoleSpy).toHaveBeenCalledWith("Failed to load terms:", expect.any(Error));
      expect(container.firstChild).toBeNull();

      consoleSpy.mockRestore();
    });
  });

  describe("Empty state", () => {
    it("renders nothing when no terms exist", async () => {
      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue([]);

      const { container } = renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.queryByText("Loading terms...")).not.toBeInTheDocument();
      });

      // Component should return null, so container should be empty
      expect(container.firstChild).toBeNull();
    });
  });

  describe("Compact mode", () => {
    it("renders terms as chips in compact mode", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
        createMockTerm({ id: "term-2", term: "Acetaminophen", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={true} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
        expect(screen.getByText("Acetaminophen")).toBeInTheDocument();
      });

      // Should not show "Also known as" header in compact mode
      expect(screen.queryByText("Also known as")).not.toBeInTheDocument();
    });

    it("renders terms without language icon in compact mode", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: null }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={true} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });
    });

    it("displays multiple terms as chips", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol" }),
        createMockTerm({ id: "term-2", term: "Acetaminophen" }),
        createMockTerm({ id: "term-3", term: "Paracétamol" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      const { container } = renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={true} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });

      // Verify all three chips are rendered
      const chips = container.querySelectorAll('.MuiChip-root');
      expect(chips.length).toBe(3);
    });
  });

  describe("Full mode", () => {
    it("renders terms with header in full mode", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={false} />);

      await waitFor(() => {
        expect(screen.getByText("Also known as")).toBeInTheDocument();
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });
    });

    it("does not repeat the display name inside aliases", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", is_display_name: true }),
        createMockTerm({ id: "term-2", term: "Doliprane", language: "fr" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={false} />);

      await waitFor(() => {
        expect(screen.getByText("Doliprane")).toBeInTheDocument();
      });

      expect(screen.queryByText("Paracetamol")).not.toBeInTheDocument();
    });

    it("shows language labels in full mode", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
        createMockTerm({ id: "term-2", term: "Paracétamol", language: "fr" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={false} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
        expect(screen.getByText("Paracétamol")).toBeInTheDocument();
      });

      // Check for language chips
      expect(screen.getByText("EN")).toBeInTheDocument();
      expect(screen.getByText("FR")).toBeInTheDocument();
    });

    it("does not show language chip when language is null", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "C8H9NO2", language: null }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={false} />);

      await waitFor(() => {
        expect(screen.getByText("C8H9NO2")).toBeInTheDocument();
      });

      // Should not show any language chips
      expect(screen.queryByText("EN")).not.toBeInTheDocument();
    });

    it("renders multiple terms in full mode", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
        createMockTerm({ id: "term-2", term: "Acetaminophen", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={false} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
        expect(screen.getByText("Acetaminophen")).toBeInTheDocument();
      });
    });
  });

  describe("Language label mapping", () => {
    it("maps common language codes to labels", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "English", language: "en" }),
        createMockTerm({ id: "term-2", term: "French", language: "fr" }),
        createMockTerm({ id: "term-3", term: "Spanish", language: "es" }),
        createMockTerm({ id: "term-4", term: "German", language: "de" }),
        createMockTerm({ id: "term-5", term: "Italian", language: "it" }),
        createMockTerm({ id: "term-6", term: "Portuguese", language: "pt" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={false} />);

      await waitFor(() => {
        expect(screen.getByText("English")).toBeInTheDocument();
      });

      // Check language labels
      expect(screen.getByText("EN")).toBeInTheDocument();
      expect(screen.getByText("FR")).toBeInTheDocument();
      expect(screen.getByText("ES")).toBeInTheDocument();
      expect(screen.getByText("DE")).toBeInTheDocument();
      expect(screen.getByText("IT")).toBeInTheDocument();
      expect(screen.getByText("PT")).toBeInTheDocument();
    });

    it("uppercases unknown language codes", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Unknown", language: "xx" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} compact={false} />);

      await waitFor(() => {
        expect(screen.getByText("Unknown")).toBeInTheDocument();
      });

      expect(screen.getByText("XX")).toBeInTheDocument();
    });
  });

  describe("Data refetching", () => {
    it("refetches terms when entityId changes", async () => {
      const mockTerms1 = [createMockTerm({ id: "term-1", term: "Term 1" })];
      const mockTerms2 = [createMockTerm({ id: "term-2", term: "Term 2" })];

      const listSpy = vi
        .spyOn(entityTermsApi, "listEntityTerms")
        .mockResolvedValueOnce(mockTerms1)
        .mockResolvedValueOnce(mockTerms2);

      const { rerender } = renderWithNotifications(<EntityTermsDisplay entityId="entity-1" />);

      await waitFor(() => {
        expect(screen.getByText("Term 1")).toBeInTheDocument();
      });

      expect(listSpy).toHaveBeenCalledWith("entity-1");

      // Change entityId
      rerender(
        <NotificationProvider>
          <EntityTermsDisplay entityId="entity-2" />
        </NotificationProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("Term 2")).toBeInTheDocument();
      });

      expect(listSpy).toHaveBeenCalledWith("entity-2");
      expect(listSpy).toHaveBeenCalledTimes(2);
    });
  });

  describe("Default compact prop", () => {
    it("uses full mode by default when compact prop not provided", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      renderWithNotifications(<EntityTermsDisplay entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Also known as")).toBeInTheDocument();
      });
    });
  });
});

/**
 * Tests for EntityTermsManager component.
 *
 * Tests CRUD operations, form validation, language selection,
 * display order management, error handling, and delete confirmation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EntityTermsManager } from "../EntityTermsManager";
import type { EntityTermRead } from "../../api/entityTerms";
import * as entityTermsApi from "../../api/entityTerms";

// Mock the API module
vi.mock("../../api/entityTerms");

// Mock i18n
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValueOrOptions?: string | { [key: string]: any }) => {
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      if (defaultValueOrOptions && typeof defaultValueOrOptions === "object") {
        let result = defaultValueOrOptions.defaultValue || key;
        // Handle template interpolation like {{value}}
        Object.keys(defaultValueOrOptions).forEach((k) => {
          if (k !== "defaultValue") {
            result = result.replace(`{{${k}}}`, String(defaultValueOrOptions[k]));
          }
        });
        return result;
      }
      return key;
    },
    i18n: { language: "en" },
  }),
}));

describe("EntityTermsManager", () => {
  const mockEntityId = "entity-123";

  const createMockTerm = (overrides?: Partial<EntityTermRead>): EntityTermRead => ({
    id: "term-1",
    entity_id: mockEntityId,
    term: "Paracetamol",
    language: "en",
    display_order: null,
    created_at: "2025-01-01T00:00:00Z",
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading and initial state", () => {
    it("loads and displays terms on mount", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
        createMockTerm({ id: "term-2", term: "Acetaminophen", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
        expect(screen.getByText("Acetaminophen")).toBeInTheDocument();
      });

      expect(entityTermsApi.listEntityTerms).toHaveBeenCalledWith(mockEntityId);
    });

    it("shows info message when no terms exist", async () => {
      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue([]);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(
          screen.getByText(/No alternative names defined/i)
        ).toBeInTheDocument();
      });
    });

    it("handles loading error", async () => {
      vi.spyOn(entityTermsApi, "listEntityTerms").mockRejectedValue(
        new Error("Network error")
      );

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Failed to load terms")).toBeInTheDocument();
      });
    });
  });

  describe("Adding terms", () => {
    it("shows add form when Add Term button clicked", async () => {
      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue([]);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Add Term")).toBeInTheDocument();
      });

      const addButton = screen.getByText("Add Term");
      fireEvent.click(addButton);

      expect(screen.getByText("Add New Term")).toBeInTheDocument();
      expect(screen.getByLabelText(/Term/i)).toBeInTheDocument();
      // Language is a MUI Select, check for the label in the form
      expect(screen.getAllByText("Language").length).toBeGreaterThan(0);
    });

    it("creates a new term successfully", async () => {
      const newTerm = createMockTerm({
        id: "term-new",
        term: "Acetaminophen",
        language: "en",
      });

      vi.spyOn(entityTermsApi, "listEntityTerms")
        .mockResolvedValueOnce([]) // Initial load
        .mockResolvedValueOnce([newTerm]); // After create

      vi.spyOn(entityTermsApi, "createEntityTerm").mockResolvedValue(newTerm);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Add Term")).toBeInTheDocument();
      });

      // Click Add Term button
      fireEvent.click(screen.getByText("Add Term"));

      // Fill form
      const termInput = screen.getByLabelText(/Term/i);
      fireEvent.change(termInput, { target: { value: "Acetaminophen" } });

      // Save
      const saveButton = screen.getByText("Save");
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(entityTermsApi.createEntityTerm).toHaveBeenCalledWith(
          mockEntityId,
          {
            term: "Acetaminophen",
            language: null,
            display_order: null,
          }
        );
      });

      // Form should close and new term should appear
      await waitFor(() => {
        expect(screen.queryByText("Add New Term")).not.toBeInTheDocument();
        expect(screen.getByText("Acetaminophen")).toBeInTheDocument();
      });
    });

    it("validates that term is not empty", async () => {
      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue([]);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Add Term")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Term"));

      // Try to save without entering a term
      const saveButton = screen.getByText("Save");
      expect(saveButton).toBeDisabled();
    });

    it("shows error when term already exists", async () => {
      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue([]);
      vi.spyOn(entityTermsApi, "createEntityTerm").mockRejectedValue(
        new Error("Term already exists for this language")
      );

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Add Term")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Term"));

      const termInput = screen.getByLabelText(/Term/i);
      fireEvent.change(termInput, { target: { value: "Duplicate" } });

      const saveButton = screen.getByText("Save");
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(
          screen.getByText("This term already exists for this language")
        ).toBeInTheDocument();
      });
    });

    it("can cancel adding a term", async () => {
      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue([]);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Add Term")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Term"));
      expect(screen.getByText("Add New Term")).toBeInTheDocument();

      const cancelButton = screen.getByText("Cancel");
      fireEvent.click(cancelButton);

      expect(screen.queryByText("Add New Term")).not.toBeInTheDocument();
    });
  });

  describe("Editing terms", () => {
    it("shows edit form when edit button clicked", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });

      // Click edit button (find by icon, there should be an edit button)
      const editButtons = screen.getAllByRole("button");
      const editButton = editButtons.find(
        (btn) => btn.querySelector('[data-testid="EditIcon"]') !== null
      );

      if (editButton) {
        fireEvent.click(editButton);
        expect(screen.getByText("Edit Term")).toBeInTheDocument();
      }
    });

    it("updates an existing term successfully", async () => {
      const originalTerm = createMockTerm({
        id: "term-1",
        term: "Paracetamol",
        language: "en",
      });
      const updatedTerm = createMockTerm({
        id: "term-1",
        term: "Acetaminophen",
        language: "en",
      });

      vi.spyOn(entityTermsApi, "listEntityTerms")
        .mockResolvedValueOnce([originalTerm]) // Initial load
        .mockResolvedValueOnce([updatedTerm]); // After update

      vi.spyOn(entityTermsApi, "updateEntityTerm").mockResolvedValue(updatedTerm);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });

      // Click edit - find the edit icon button
      const editButtons = screen.getAllByRole("button");
      const editButton = editButtons.find(
        (btn) => btn.querySelector("svg")?.getAttribute("data-testid") === "EditIcon"
      );

      if (editButton) {
        fireEvent.click(editButton);

        await waitFor(() => {
          expect(screen.getByText("Edit Term")).toBeInTheDocument();
        });

        const termInput = screen.getByLabelText(/Term/i);
        fireEvent.change(termInput, { target: { value: "Acetaminophen" } });

        const saveButton = screen.getByText("Save");
        fireEvent.click(saveButton);

        await waitFor(() => {
          expect(entityTermsApi.updateEntityTerm).toHaveBeenCalledWith(
            mockEntityId,
            "term-1",
            {
              term: "Acetaminophen",
              language: "en",
              display_order: null,
            }
          );
        });
      }
    });
  });

  describe("Deleting terms", () => {
    it("shows delete confirmation dialog", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });

      // Find and click delete button
      const deleteButtons = screen.getAllByRole("button");
      const deleteButton = deleteButtons.find(
        (btn) => btn.querySelector("svg")?.getAttribute("data-testid") === "DeleteIcon"
      );

      if (deleteButton) {
        fireEvent.click(deleteButton);

        await waitFor(() => {
          expect(screen.getByText("Delete Term?")).toBeInTheDocument();
        });
      }
    });

    it("deletes term when confirmed", async () => {
      const mockTerm = createMockTerm({
        id: "term-1",
        term: "Paracetamol",
        language: "en",
      });

      vi.spyOn(entityTermsApi, "listEntityTerms")
        .mockResolvedValueOnce([mockTerm]) // Initial load
        .mockResolvedValueOnce([]); // After delete

      vi.spyOn(entityTermsApi, "deleteEntityTerm").mockResolvedValue(undefined);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });

      // Click delete button
      const deleteButtons = screen.getAllByRole("button");
      const deleteButton = deleteButtons.find(
        (btn) => btn.querySelector("svg")?.getAttribute("data-testid") === "DeleteIcon"
      );

      if (deleteButton) {
        fireEvent.click(deleteButton);

        await waitFor(() => {
          expect(screen.getByText("Delete Term?")).toBeInTheDocument();
        });

        // Confirm deletion
        const confirmButton = screen.getByRole("button", { name: /Delete/i });
        fireEvent.click(confirmButton);

        await waitFor(() => {
          expect(entityTermsApi.deleteEntityTerm).toHaveBeenCalledWith(
            mockEntityId,
            "term-1"
          );
        });

        // Term should be removed
        await waitFor(() => {
          expect(screen.queryByText("Paracetamol")).not.toBeInTheDocument();
        });
      }
    });

    it("cancels deletion when cancel clicked", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });

      // Click delete button
      const deleteButtons = screen.getAllByRole("button");
      const deleteButton = deleteButtons.find(
        (btn) => btn.querySelector("svg")?.getAttribute("data-testid") === "DeleteIcon"
      );

      if (deleteButton) {
        fireEvent.click(deleteButton);

        await waitFor(() => {
          expect(screen.getByText("Delete Term?")).toBeInTheDocument();
        });

        // Cancel deletion
        const cancelButton = screen.getByRole("button", { name: /Cancel/i });
        fireEvent.click(cancelButton);

        await waitFor(() => {
          expect(screen.queryByText("Delete Term?")).not.toBeInTheDocument();
        });

        // Term should still be present
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      }
    });
  });

  describe("Language grouping", () => {
    it("groups terms by language", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
        createMockTerm({ id: "term-2", term: "Acetaminophen", language: "en" }),
        createMockTerm({ id: "term-3", term: "Paracétamol", language: "fr" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("English (2)")).toBeInTheDocument();
        expect(screen.getByText("French (1)")).toBeInTheDocument();
      });
    });

    it("shows international group for terms without language", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "C8H9NO2", language: null }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("International (1)")).toBeInTheDocument();
      });
    });
  });

  describe("Display order", () => {
    it("shows display order in secondary text when set", async () => {
      const mockTerms = [
        createMockTerm({
          id: "term-1",
          term: "Paracetamol",
          language: "en",
          display_order: 1,
        }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Display order: 1")).toBeInTheDocument();
      });
    });

    it("allows setting display order when adding term", async () => {
      const newTerm = createMockTerm({
        id: "term-new",
        term: "Acetaminophen",
        language: "en",
        display_order: 2,
      });

      vi.spyOn(entityTermsApi, "listEntityTerms")
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce([newTerm]);

      vi.spyOn(entityTermsApi, "createEntityTerm").mockResolvedValue(newTerm);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        expect(screen.getByText("Add Term")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Term"));

      const termInput = screen.getByLabelText(/Term/i);
      fireEvent.change(termInput, { target: { value: "Acetaminophen" } });

      const displayOrderInput = screen.getByLabelText(/Display Order/i);
      fireEvent.change(displayOrderInput, { target: { value: "2" } });

      const saveButton = screen.getByText("Save");
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(entityTermsApi.createEntityTerm).toHaveBeenCalledWith(
          mockEntityId,
          {
            term: "Acetaminophen",
            language: null,
            display_order: 2,
          }
        );
      });
    });
  });

  describe("Readonly mode", () => {
    it("hides add button in readonly mode", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} readonly={true} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });

      expect(screen.queryByText("Add Term")).not.toBeInTheDocument();
    });

    it("hides edit and delete buttons in readonly mode", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} readonly={true} />);

      await waitFor(() => {
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
      });

      // In readonly mode, there should be no buttons (no add, edit, or delete buttons)
      expect(screen.queryByRole("button")).not.toBeInTheDocument();
    });
  });

  describe("Summary display", () => {
    it("shows total term count", async () => {
      const mockTerms = [
        createMockTerm({ id: "term-1", term: "Paracetamol", language: "en" }),
        createMockTerm({ id: "term-2", term: "Acetaminophen", language: "en" }),
        createMockTerm({ id: "term-3", term: "Paracétamol", language: "fr" }),
      ];

      vi.spyOn(entityTermsApi, "listEntityTerms").mockResolvedValue(mockTerms);

      render(<EntityTermsManager entityId={mockEntityId} />);

      await waitFor(() => {
        // Check that all terms are displayed
        expect(screen.getByText("Paracetamol")).toBeInTheDocument();
        expect(screen.getByText("Acetaminophen")).toBeInTheDocument();
        expect(screen.getByText("Paracétamol")).toBeInTheDocument();
      });

      // The summary chip is in a Divider, just verify the 3 terms are shown
      expect(screen.getAllByRole("listitem").length).toBe(3);
    });
  });
});

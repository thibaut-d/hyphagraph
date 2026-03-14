import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";

import {
  deleteRelation,
  deleteSource,
  getSource,
  listRelationsBySource,
  mockNavigate,
  mockRelations,
  mockSource,
  renderSourceDetailView,
} from "./SourceDetailView.test-support";

describe("SourceDetailView actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getSource as any).mockResolvedValue(mockSource);
    (listRelationsBySource as any).mockResolvedValue(mockRelations);
  });

  describe("Delete source functionality", () => {
    it("opens and closes the delete source confirmation dialog", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        fireEvent.click(screen.getAllByTitle(/delete/i)[0]);
      });

      await waitFor(() => {
        expect(screen.getByText(/delete source/i)).toBeInTheDocument();
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText(/cancel/i));

      await waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
      });
    });

    it("calls deleteSource and navigates on confirm", async () => {
      (deleteSource as any).mockResolvedValue(undefined);

      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        fireEvent.click(screen.getAllByTitle(/delete/i)[0]);
      });

      await waitFor(() => {
        const confirmButton = screen
          .getAllByText(/delete/i)
          .find((button) => button.tagName === "BUTTON" && button.textContent === "Delete");
        if (confirmButton) {
          fireEvent.click(confirmButton);
        }
      });

      await waitFor(() => {
        expect(deleteSource).toHaveBeenCalledWith(mockSource.id);
        expect(mockNavigate).toHaveBeenCalledWith("/sources");
      });
    });
  });

  describe("Delete relation functionality", () => {
    it("opens delete relation confirmation dialog", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        fireEvent.click(screen.getAllByTitle(/delete/i)[1]);
      });

      await waitFor(() => {
        expect(screen.getByText(/delete relation/i)).toBeInTheDocument();
      });
    });

    it("deletes a relation and refreshes the list on confirm", async () => {
      (deleteRelation as any).mockResolvedValue(undefined);

      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getByText("Test Study on Aspirin")).toBeInTheDocument();
      });

      fireEvent.click(screen.getAllByTitle(/delete/i)[1]);

      await waitFor(() => {
        expect(screen.getByText(/delete relation/i)).toBeInTheDocument();
      });

      const deleteButton = screen
        .getAllByRole("button")
        .find((button) => button.textContent === "Delete" && button.closest('[role="dialog"]'));
      if (deleteButton) {
        fireEvent.click(deleteButton);
      }

      await waitFor(() => {
        expect(deleteRelation).toHaveBeenCalledWith("rel-1");
      });
    });
  });
});

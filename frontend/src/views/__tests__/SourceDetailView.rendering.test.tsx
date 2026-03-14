import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import {
  getSource,
  listRelationsBySource,
  mockRelations,
  mockSource,
  renderSourceDetailView,
} from "./SourceDetailView.test-support";

describe("SourceDetailView rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Source display", () => {
    beforeEach(() => {
      (getSource as any).mockResolvedValue(mockSource);
      (listRelationsBySource as any).mockResolvedValue(mockRelations);
    });

    it("displays source title", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getByText("Test Study on Aspirin")).toBeInTheDocument();
      });
    });

    it("displays source kind", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getAllByText(/study/i).length).toBeGreaterThan(0);
      });
    });

    it("displays source year", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getByText("2020")).toBeInTheDocument();
      });
    });

    it("displays trust level percentage", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getByText("Quality: 85%")).toBeInTheDocument();
      });
    });

    it("shows source action buttons", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getAllByTitle(/edit/i).length).toBeGreaterThan(0);
        expect(screen.getAllByTitle(/delete/i).length).toBeGreaterThan(0);
      });
    });
  });

  describe("Relations display", () => {
    beforeEach(() => {
      (getSource as any).mockResolvedValue(mockSource);
      (listRelationsBySource as any).mockResolvedValue(mockRelations);
    });

    it("displays the relations section and relation rows", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getByRole("heading", { name: "Relations" })).toBeInTheDocument();
        expect(screen.getByText("effect")).toBeInTheDocument();
        expect(screen.getByText("mechanism")).toBeInTheDocument();
        expect(screen.getByText("positive")).toBeInTheDocument();
        expect(screen.getByText("supports")).toBeInTheDocument();
      });
    });

    it("shows entity links and per-relation action buttons", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getAllByRole("link").length).toBeGreaterThan(0);
        expect(screen.getAllByTitle(/edit/i).length).toBeGreaterThanOrEqual(3);
        expect(screen.getAllByTitle(/delete/i).length).toBeGreaterThanOrEqual(3);
      });
    });
  });

  describe("Empty relations", () => {
    beforeEach(() => {
      (getSource as any).mockResolvedValue(mockSource);
      (listRelationsBySource as any).mockResolvedValue([]);
    });

    it("displays no relations message when empty", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getByText(/no relations/i)).toBeInTheDocument();
      });
    });
  });
});

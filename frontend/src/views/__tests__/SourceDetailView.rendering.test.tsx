import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import {
  getSource,
  listRelationsBySource,
  mockRelations,
  mockSource,
  renderSourceDetailViewAt,
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
        // Title appears in both the breadcrumb and the h4 heading; use heading role for specificity
        expect(screen.getByRole("heading", { name: "Test Study on Aspirin" })).toBeInTheDocument();
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
        expect(screen.getByText("Evidence weight: 85%")).toBeInTheDocument();
        expect(screen.getAllByText("Quality: 85%").length).toBeGreaterThanOrEqual(1);
      });
    });

    it("shows source action buttons", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getAllByTitle(/edit/i).length).toBeGreaterThan(0);
        expect(screen.getAllByTitle(/delete/i).length).toBeGreaterThan(0);
      });
    });

    it("shows the verification summary and document summary before extraction controls", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getByText("Verification summary")).toBeInTheDocument();
        expect(screen.getByText("Document summary")).toBeInTheDocument();
        expect(
          screen.getByText("This study reports that aspirin reduced platelet aggregation in the observed cohort."),
        ).toBeInTheDocument();
      });

      const verificationSummary = screen.getByText("Verification summary");
      const evidenceSection = screen.getByRole("heading", { name: "Source-backed statements" });
      const extractionSection = screen.getByRole("heading", { name: "Knowledge Extraction" });

      expect(
        verificationSummary.compareDocumentPosition(evidenceSection) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
      expect(
        evidenceSection.compareDocumentPosition(extractionSection) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
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
        expect(screen.getByRole("heading", { name: "Linked relations and entities" })).toBeInTheDocument();
        expect(screen.getAllByText("effect").length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText("mechanism").length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText("positive")).toBeInTheDocument();
        expect(screen.getAllByText("supports").length).toBeGreaterThanOrEqual(1);
      });
    });

    it("renders a dedicated recorded statements layer with relation evidence links", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getByText("Recorded statements")).toBeInTheDocument();
        expect(screen.getByText('"Aspirin inhibits cyclooxygenase in platelets."')).toBeInTheDocument();
      });

      expect(screen.getByRole("link", { name: "Open relation evidence" })).toHaveAttribute(
        "href",
        "/relations/rel-2",
      );
    });

    it("shows entity links and per-relation action buttons", async () => {
      renderSourceDetailView(mockSource.id);

      await waitFor(() => {
        expect(screen.getAllByRole("link").length).toBeGreaterThan(0);
        expect(screen.getAllByTitle(/edit/i).length).toBeGreaterThanOrEqual(3);
        expect(screen.getAllByTitle(/delete/i).length).toBeGreaterThanOrEqual(3);
      });

      expect(screen.getByRole("link", { name: "aspirin" })).toHaveAttribute(
        "href",
        "/entities/aspirin",
      );
      expect(screen.getByRole("link", { name: "platelets" })).toHaveAttribute(
        "href",
        "/entities/platelets",
      );
      expect(screen.getAllByText("(Drug)")).toHaveLength(2);
    });

    it("highlights and anchors the requested relation from evidence navigation", async () => {
      window.HTMLElement.prototype.scrollIntoView = vi.fn();

      renderSourceDetailViewAt(`/sources/${mockSource.id}?relation=rel-2#relation-rel-2`);

      await waitFor(() => {
        expect(document.getElementById("relation-rel-2")).toHaveAttribute("data-highlighted", "true");
      });

      const highlightedRow = document.getElementById("relation-rel-2");
      expect(highlightedRow).toHaveAttribute("data-highlighted", "true");
      expect(screen.getByText("Requested from evidence trace")).toBeInTheDocument();
      expect(screen.getByText("Aspirin inhibits cyclooxygenase in platelets.")).toBeInTheDocument();

      await waitFor(() => {
        expect(window.HTMLElement.prototype.scrollIntoView).toHaveBeenCalled();
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

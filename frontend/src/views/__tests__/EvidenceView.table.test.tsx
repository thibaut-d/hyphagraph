import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import {
  clickSortableHeader,
  mockSuccessfulEvidenceData,
  renderEvidenceView,
} from "./EvidenceView.test-support";

describe("EvidenceView table", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
    mockSuccessfulEvidenceData();
  });

  it("renders the evidence table with relation content", async () => {
    renderEvidenceView();

    await waitFor(() => {
      expect(screen.getByText("evidence.header_all")).toBeInTheDocument();
      expect(screen.getByText("evidence.table.claim")).toBeInTheDocument();
      expect(screen.getByText("evidence.table.direction")).toBeInTheDocument();
      expect(screen.getByText("evidence.table.confidence")).toBeInTheDocument();
    });

    expect(screen.getAllByText("treats").length).toBeGreaterThan(0);
    expect(screen.getByText("causes_side_effect")).toBeInTheDocument();
  });

  it("displays direction chips, confidence, sources, roles, notes, and count badge", async () => {
    renderEvidenceView();

    await waitFor(() => {
      expect(screen.getAllByText("evidence.supports")).toHaveLength(2);
      expect(screen.getAllByText("evidence.contradicts")).toHaveLength(1);
      expect(screen.getByText("80%")).toBeInTheDocument();
      expect(screen.getByText("60%")).toBeInTheDocument();
      expect(screen.getByText("90%")).toBeInTheDocument();
      expect(screen.getByText("Clinical Trial A")).toBeInTheDocument();
      expect(screen.getByText("Observational Study B")).toBeInTheDocument();
      expect(screen.getByText("Meta-Analysis C")).toBeInTheDocument();
      expect(screen.getAllByText(/agent:/)).toHaveLength(3);
    });

    expect(screen.getByText(/patient:/)).toBeInTheDocument();
    expect(screen.getByText(/outcome:/)).toBeInTheDocument();
    expect(screen.getByText(/Smith, J., Doe, A./)).toBeInTheDocument();
    expect(screen.getByText(/Johnson, K./)).toBeInTheDocument();
    expect(screen.getByText(/Brown, L., White, M. et al./)).toBeInTheDocument();
    expect(
      screen.getAllByRole("button").filter((button) => button.querySelector('[data-testid="HelpIcon"]')).length
    ).toBeGreaterThanOrEqual(1);

    await waitFor(() => {
      expect(screen.getAllByRole("row")).toHaveLength(4);
    });
  });

  it("allows sorting by confidence, kind, and direction", async () => {
    renderEvidenceView();

    await waitFor(() => {
      expect(screen.getAllByRole("row")).toHaveLength(4);
    });

    clickSortableHeader("evidence.table.confidence");
    clickSortableHeader("evidence.table.claim");
    clickSortableHeader("evidence.table.direction");

    expect(screen.getByText("evidence.table.confidence")).toBeInTheDocument();
    expect(screen.getByText("evidence.table.claim")).toBeInTheDocument();
    expect(screen.getByText("evidence.table.direction")).toBeInTheDocument();
  });

  it("shows filtered headers and filtered relations when a role type is provided", async () => {
    renderEvidenceView("/entities/entity-1/properties/patient/evidence");

    await waitFor(() => {
      expect(screen.getByText(/evidence.header_filtered/)).toBeInTheDocument();
      expect(screen.getAllByRole("row").length).toBe(2);
    });

    expect(screen.getByText("treats")).toBeInTheDocument();
    expect(screen.queryByText("causes_side_effect")).not.toBeInTheDocument();
  });
});

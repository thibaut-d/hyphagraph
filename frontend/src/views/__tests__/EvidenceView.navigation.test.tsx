import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import {
  mockSuccessfulEvidenceData,
  renderEvidenceView,
} from "./EvidenceView.test-support";

describe("EvidenceView navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
    mockSuccessfulEvidenceData();
  });

  it("renders breadcrumbs and the back button", async () => {
    renderEvidenceView();

    await waitFor(() => {
      expect(screen.getByText("evidence.header_all")).toBeInTheDocument();
    });

    expect(screen.getByText("menu.entities")).toBeInTheDocument();
    expect(screen.getAllByText("Paracetamol").length).toBeGreaterThan(0);
    expect(screen.getByText("evidence.title")).toBeInTheDocument();
    expect(screen.getByText("common.back")).toBeInTheDocument();
  });

  it("displays the scientific audit note", async () => {
    renderEvidenceView();

    await waitFor(() => {
      expect(screen.getByText(/evidence.audit_note/)).toBeInTheDocument();
    });
  });
});

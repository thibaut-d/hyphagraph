import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import {
  mockEntity,
  mockEvidenceEntityPending,
  mockEvidenceEntityRejected,
  mockEvidenceEntityResolved,
  mockEvidenceInferencePending,
  mockEvidenceInferenceResolved,
  mockInference,
  renderEvidenceView,
} from "./EvidenceView.test-support";

describe("EvidenceView states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("shows loading state initially", () => {
    mockEvidenceEntityPending();
    mockEvidenceInferencePending();

    renderEvidenceView();

    expect(screen.getByText("evidence.loading")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows entity fetch errors inline", async () => {
    mockEvidenceEntityRejected(new Error("Entity not found"));
    mockEvidenceInferenceResolved(mockInference);

    renderEvidenceView();

    await waitFor(() => {
      expect(screen.getByText("Entity not found")).toBeInTheDocument();
    });
  });

  it("shows parsed backend error messages inline", async () => {
    mockEvidenceEntityRejected({
      code: "RATE_LIMIT_EXCEEDED",
      message: "Too many requests. Please try again later.",
      details: "Evidence endpoint rate limited",
    });
    mockEvidenceInferenceResolved(mockInference);

    renderEvidenceView();

    await waitFor(() => {
      expect(screen.getAllByText("Too many requests. Please try again later.").length).toBeGreaterThan(0);
    });
  });

  it("shows error when the route entity id is invalid", async () => {
    mockEvidenceEntityRejected(new Error("Failed to load evidence"));
    mockEvidenceInferenceResolved(mockInference);

    renderEvidenceView("/entities/undefined/evidence");

    await waitFor(() => {
      expect(screen.getAllByText("Failed to load evidence").length).toBeGreaterThan(0);
    });
  });

  it("shows the empty state when no relations exist", async () => {
    mockEvidenceEntityResolved(mockEntity);
    mockEvidenceInferenceResolved({
      entity_id: "entity-1",
      relations_by_kind: {},
    });

    renderEvidenceView();

    await waitFor(() => {
      expect(screen.getByText("evidence.no_data.title")).toBeInTheDocument();
      expect(screen.getByText("evidence.no_data.all")).toBeInTheDocument();
    });
  });

  it("shows the filtered empty state when no relations match the role type", async () => {
    mockEvidenceEntityResolved(mockEntity);
    mockEvidenceInferenceResolved(mockInference);

    renderEvidenceView("/entities/entity-1/properties/nonexistent/evidence");

    await waitFor(() => {
      expect(screen.getByText("evidence.no_data.filtered")).toBeInTheDocument();
    });
  });
});

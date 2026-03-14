import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import {
  createMockInference,
  mockEntity,
  mockSynthesisEntityPending,
  mockSynthesisEntityRejected,
  mockSynthesisEntityResolved,
  mockSynthesisInferencePending,
  mockSynthesisInferenceRejected,
  mockSynthesisInferenceResolved,
  renderSynthesisView,
} from "./SynthesisView.test-support";

describe("SynthesisView states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    mockSynthesisEntityPending();
    mockSynthesisInferencePending();

    renderSynthesisView();

    expect(screen.getByText("Generating synthesis...")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows entity fetch errors", async () => {
    mockSynthesisEntityRejected(new Error("Entity not found"));
    mockSynthesisInferenceResolved(createMockInference());

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Entity not found/i).length).toBeGreaterThan(0);
    });
  });

  it("shows inference fetch errors", async () => {
    mockSynthesisEntityResolved(mockEntity);
    mockSynthesisInferenceRejected(new Error("Failed to load synthesis"));

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Failed to load synthesis/i).length).toBeGreaterThan(0);
    });
  });

  it("shows the no-data state when no relations exist", async () => {
    const inference = createMockInference({ relations_by_kind: {} });
    mockSynthesisEntityResolved(mockEntity);
    mockSynthesisInferenceResolved(inference);

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText("No synthesized knowledge available")).toBeInTheDocument();
    });

    expect(screen.queryByText("Total Relations")).not.toBeInTheDocument();
    expect(screen.queryByText("Unique Sources")).not.toBeInTheDocument();
  });
});

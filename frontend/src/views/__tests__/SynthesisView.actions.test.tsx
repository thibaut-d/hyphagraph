import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  createMockInference,
  createMockRelation,
  mockNavigate,
  mockSuccessfulSynthesisData,
  renderSynthesisView,
} from "./SynthesisView.test-support";

describe("SynthesisView actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders grouped relations with counts and confidence summaries", async () => {
    mockSuccessfulSynthesisData();

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText("Relations by Type")).toBeInTheDocument();
      expect(screen.getAllByText("treats").length).toBeGreaterThan(0);
      expect(screen.getByText("2 relations")).toBeInTheDocument();
      expect(screen.getByText("1 relation")).toBeInTheDocument();
      expect(screen.getByText("88% confidence")).toBeInTheDocument();
      expect(screen.getByText("75% confidence")).toBeInTheDocument();
    });
  });

  it("shows the disagreements action when contradictions exist and navigates correctly", async () => {
    const user = userEvent.setup();
    mockSuccessfulSynthesisData(
      createMockInference({
        relations_by_kind: {
          treats: [createMockRelation({ direction: "contradicts" })],
        },
      })
    );

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText(/View Disagreements/)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/View Disagreements/));
    expect(mockNavigate).toHaveBeenCalledWith("/entities/entity-123/disagreements");
  });

  it("navigates back to entity detail from the back button", async () => {
    const user = userEvent.setup();
    mockSuccessfulSynthesisData();

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText("Back to entity")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Back to entity"));
    expect(mockNavigate).toHaveBeenCalledWith("/entities/entity-123");
  });
});

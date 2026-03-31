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

  it("shows representative evidence statements and a single explicit property-detail action", async () => {
    const user = userEvent.setup();
    mockSuccessfulSynthesisData(
      createMockInference({
        relations_by_kind: {
          treats: [
            createMockRelation({
              id: "rel-1",
              kind: "treats",
              source_id: "source-1",
              direction: "supports",
              roles: [
                { id: "role-1", relation_revision_id: "rev-1", entity_id: "drug-1", entity_slug: "paracetamol", role_type: "subject" },
                { id: "role-2", relation_revision_id: "rev-1", entity_id: "condition-1", entity_slug: "fever", role_type: "object" },
              ],
              scope: { population: "adults" },
            }),
            createMockRelation({
              id: "rel-2",
              kind: "treats",
              source_id: "source-2",
              direction: "contradicts",
              roles: [
                { id: "role-3", relation_revision_id: "rev-2", entity_id: "drug-1", entity_slug: "paracetamol", role_type: "subject" },
                { id: "role-4", relation_revision_id: "rev-2", entity_id: "condition-2", entity_slug: "headache", role_type: "object" },
              ],
            }),
          ],
        },
      }),
    );

    renderSynthesisView();

    const treatsSection = await screen.findByText("treats");
    await user.click(treatsSection);

    expect(screen.getByText(/Representative evidence statements are shown below/i)).toBeInTheDocument();
    expect(screen.getByText("paracetamol treats fever")).toBeInTheDocument();
    expect(screen.getByText(/Supports • Confidence: 85% • Population: adults/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open property detail" })).toBeInTheDocument();
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

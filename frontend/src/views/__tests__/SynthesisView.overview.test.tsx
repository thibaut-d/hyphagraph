import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import {
  createMockInference,
  createMockRelation,
  mockSuccessfulSynthesisData,
  renderSynthesisView,
} from "./SynthesisView.test-support";

describe("SynthesisView overview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders synthesis identity and breadcrumbs", async () => {
    mockSuccessfulSynthesisData();

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText("Evidence Synthesis")).toBeInTheDocument();
      expect(screen.getAllByText("Paracetamol").length).toBeGreaterThan(0);
      expect(screen.getByText("Entities")).toBeInTheDocument();
      expect(screen.getByText("Synthesis")).toBeInTheDocument();
      expect(screen.getByText("Back to entity")).toBeInTheDocument();
    });
  });

  it("surfaces contradiction counts in relation summaries", async () => {
    mockSuccessfulSynthesisData(
      createMockInference({
        relations_by_kind: {
          treats: [
            createMockRelation({ id: "rel-1", direction: "supports", source_id: "source-1" }),
            createMockRelation({ id: "rel-2", direction: "contradicts", source_id: "source-2" }),
          ],
        },
      })
    );

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText("1 contradiction")).toBeInTheDocument();
    });
  });

  it("displays synthesis statistics", async () => {
    mockSuccessfulSynthesisData();

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText("Total Relations")).toBeInTheDocument();
      expect(screen.getByText("Unique Sources")).toBeInTheDocument();
      expect(screen.getByText("Avg. Confidence")).toBeInTheDocument();
      expect(screen.getByText("Relation Types")).toBeInTheDocument();
      expect(screen.getByText("83%")).toBeInTheDocument();
    });

    expect(screen.getAllByText("3").length).toBeGreaterThan(0);
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("displays evidence quality indicators", async () => {
    mockSuccessfulSynthesisData();

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText("Evidence Quality Overview")).toBeInTheDocument();
      expect(screen.getByText(/High Confidence/)).toBeInTheDocument();
    });
  });

  it("shows low confidence and contradictions when present", async () => {
    mockSuccessfulSynthesisData(
      createMockInference({
        relations_by_kind: {
          treats: [
            createMockRelation({ confidence: 0.3, source_id: "source-1" }),
            createMockRelation({ direction: "contradicts", source_id: "source-2" }),
          ],
        },
      })
    );

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText(/Low Confidence/)).toBeInTheDocument();
      expect(screen.getByText(/Contradictions/)).toBeInTheDocument();
    });
  });

  it("shows and hides knowledge gap messaging based on relation breadth", async () => {
    mockSuccessfulSynthesisData(
      createMockInference({
        relations_by_kind: {
          treats: [createMockRelation()],
        },
      })
    );

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText("Knowledge Gaps Detected")).toBeInTheDocument();
      expect(screen.getByText(/limited relation types/i)).toBeInTheDocument();
    });
  });

  it("hides knowledge gap messaging when relation breadth is sufficient", async () => {
    mockSuccessfulSynthesisData(
      createMockInference({
        relations_by_kind: {
          treats: [createMockRelation()],
          causes: [createMockRelation()],
          prevents: [createMockRelation()],
        },
      })
    );

    renderSynthesisView();

    await waitFor(() => {
      expect(screen.getByText("Relations by Type")).toBeInTheDocument();
    });

    expect(screen.queryByText("Knowledge Gaps Detected")).not.toBeInTheDocument();
  });
});

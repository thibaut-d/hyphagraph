import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExtractedRelationsList } from "../ExtractedRelationsList";
import type { ExtractedRelation } from "../../types/extraction";

const naryRelation: ExtractedRelation = {
  relation_type: "treats",
  roles: [
    { entity_slug: "duloxetine", role_type: "agent" },
    { entity_slug: "juvenile-fibromyalgia", role_type: "target" },
    { entity_slug: "adolescents", role_type: "population" },
    { entity_slug: "pain-intensity", role_type: "outcome" },
    { entity_slug: "placebo", role_type: "control_group" },
  ],
  confidence: "high",
  text_span:
    "Duloxetine demonstrated modest improvements in pain among adolescents with juvenile fibromyalgia compared with placebo.",
  notes: "Reported as a modest improvement with adverse effects.",
  study_context: {
    statement_kind: "finding",
    finding_polarity: "supports",
    evidence_strength: "strong",
    study_design: "randomized_controlled_trial",
    sample_size: 120,
    sample_size_text: "n=120",
    assertion_text: "Duloxetine improved pain compared with placebo in adolescents with juvenile fibromyalgia.",
    methodology_text: "Randomized placebo-controlled comparison.",
    statistical_support: "p=0.01",
  },
};

describe("ExtractedRelationsList", () => {
  it("renders n-ary relation roles directly instead of reducing the relation to subject and object", () => {
    render(
      <ExtractedRelationsList
        relations={[naryRelation]}
        selectedRelations={new Set(["selected"])}
        onToggle={vi.fn()}
      />,
    );

    expect(screen.getByText("Treats")).toBeInTheDocument();
    expect(screen.getByText("agent")).toBeInTheDocument();
    expect(screen.getByText("duloxetine")).toBeInTheDocument();
    expect(screen.getByText("target")).toBeInTheDocument();
    expect(screen.getByText("juvenile-fibromyalgia")).toBeInTheDocument();
    expect(screen.getByText("population")).toBeInTheDocument();
    expect(screen.getByText("adolescents")).toBeInTheDocument();
    expect(screen.getByText("outcome")).toBeInTheDocument();
    expect(screen.getByText("pain-intensity")).toBeInTheDocument();
    expect(screen.getByText("control_group")).toBeInTheDocument();
    expect(screen.getByText("placebo")).toBeInTheDocument();
    expect(screen.getByText("Finding")).toBeInTheDocument();
    expect(screen.getByText("Supports")).toBeInTheDocument();
    expect(screen.getByText("Evidence: strong")).toBeInTheDocument();
    expect(screen.getByText("Randomized trial")).toBeInTheDocument();
    expect(screen.getByText("n=120")).toBeInTheDocument();
    expect(screen.getByText("Core statement")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Duloxetine improved pain compared with placebo in adolescents with juvenile fibromyalgia.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Method / applicability")).toBeInTheDocument();
    expect(screen.getByText("Randomized placebo-controlled comparison.")).toBeInTheDocument();
    expect(screen.getByText("Statistical support")).toBeInTheDocument();
    expect(screen.getByText("p=0.01")).toBeInTheDocument();
    expect(
      screen.getByText(
        '"Duloxetine demonstrated modest improvements in pain among adolescents with juvenile fibromyalgia compared with placebo."',
      ),
    ).toBeInTheDocument();
  });
});

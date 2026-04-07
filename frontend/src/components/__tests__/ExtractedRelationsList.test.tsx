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
    expect(
      screen.getByText(
        '"Duloxetine demonstrated modest improvements in pain among adolescents with juvenile fibromyalgia compared with placebo."',
      ),
    ).toBeInTheDocument();
  });
});

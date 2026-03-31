import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router";

import { InferenceBlock } from "../InferenceBlock";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (
      key: string,
      defaultValueOrOptions?: string | { defaultValue?: string; [key: string]: unknown },
    ) => {
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      if (defaultValueOrOptions && typeof defaultValueOrOptions === "object") {
        let result = defaultValueOrOptions.defaultValue || key;
        Object.entries(defaultValueOrOptions).forEach(([field, value]) => {
          if (field !== "defaultValue") {
            result = result.replace(`{{${field}}}`, String(value));
          }
        });
        return result;
      }
      return key;
    },
  }),
}));

describe("InferenceBlock", () => {
  it("renders the evidence-reading guidance and labeled score semantics", () => {
    const mockInference = {
      entity_id: "entity-123",
      role_inferences: [
        {
          role_type: "therapeutic_use",
          score: 0.62,
          coverage: 4,
          confidence: 0.83,
          disagreement: 0.12,
        },
      ],
      relations_by_kind: {
        treats: [
          {
            id: "rel-1",
            source_id: "source-1",
            kind: "treats",
            direction: "supports",
            confidence: 0.88,
            notes: "Observed in adult migraine cohorts",
            scope: { population: "adults" },
            roles: [
              { entity_id: "drug-1", entity_slug: "aspirin", role_type: "subject" },
              { entity_id: "condition-1", entity_slug: "migraine", role_type: "object" },
            ],
            created_at: new Date().toISOString(),
          },
        ],
      },
    };

    render(
      <BrowserRouter>
        <InferenceBlock inference={mockInference} />
      </BrowserRouter>,
    );

    expect(screen.getByText("Computed Reading of the Evidence")).toBeInTheDocument();
    expect(
      screen.getByText(/computed interpretation of the evidence base, not an unquestionable conclusion/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/score shows whether evidence leans supportive or contradictory/i)).toBeInTheDocument();
    expect(screen.getByText("More contradicting evidence")).toBeInTheDocument();
    expect(screen.getByText("Mixed or limited signal")).toBeInTheDocument();
    expect(screen.getByText("More supporting evidence")).toBeInTheDocument();
    expect(screen.getByText("4 relations reviewed")).toBeInTheDocument();
    expect(screen.getByText("83% confidence")).toBeInTheDocument();
    expect(screen.getByText("12% disagreement")).toBeInTheDocument();
  });

  it("renders source evidence as readable claims with context and source links", () => {
    const mockInference = {
      entity_id: "entity-123",
      relations_by_kind: {
        effect: [
          {
            id: "rel-1",
            source_id: "source-1",
            kind: "effect",
            direction: "positive",
            confidence: 0.8,
            scope: { population: "adults" },
            notes: "Pain reduction observed within 24 hours",
            roles: [
              { entity_id: "drug-1", entity_slug: "aspirin", role_type: "subject" },
              { entity_id: "outcome-1", entity_slug: "pain relief", role_type: "object" },
            ],
            created_at: new Date().toISOString(),
          },
        ],
      },
    };

    render(
      <BrowserRouter>
        <InferenceBlock inference={mockInference} />
      </BrowserRouter>,
    );

    expect(
      screen.getByText(/These source-backed relations are the evidence the computed reading is built from/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Supports")).toBeInTheDocument();
    expect(screen.getByText("Evidence confidence: 80%")).toBeInTheDocument();
    expect(screen.getByText("aspirin effect pain relief")).toBeInTheDocument();
    expect(screen.getByText(/Population: adults/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open source evidence/i })).toHaveAttribute(
      "href",
      "/sources/source-1",
    );
  });

  it("handles null inference gracefully", () => {
    render(
      <BrowserRouter>
        <InferenceBlock inference={null} />
      </BrowserRouter>,
    );

    expect(screen.queryByText(/source evidence/i)).not.toBeInTheDocument();
  });
});

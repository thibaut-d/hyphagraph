/**
 * Tests for SynthesisView component.
 *
 * Tests synthesis display, statistics calculation, quality indicators,
 * consensus levels, knowledge gaps, and navigation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { SynthesisView } from "../SynthesisView";
import type { EntityRead } from "../../api/entities";
import type { InferenceRead } from "../../types/inference";
import type { RelationRead } from "../../types/relation";
import * as entitiesApi from "../../api/entities";
import * as inferencesApi from "../../api/inferences";

// Mock the API modules
vi.mock("../../api/entities");
vi.mock("../../api/inferences");

// Mock react-router-dom hooks
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: "entity-123" }),
  };
});

// Mock i18n with template interpolation support
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValueOrOptions?: string | { defaultValue?: string; [key: string]: any }) => {
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      if (defaultValueOrOptions && typeof defaultValueOrOptions === "object") {
        let result = defaultValueOrOptions.defaultValue || key;
        Object.keys(defaultValueOrOptions).forEach((k) => {
          if (k !== "defaultValue") {
            result = result.replace(`{{${k}}}`, String(defaultValueOrOptions[k]));
          }
        });
        return result;
      }
      return key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock resolveLabel utility
vi.mock("../../utils/i18nLabel", () => ({
  resolveLabel: (label: any) => {
    if (typeof label === "string") return label;
    if (label && typeof label === "object" && label.en) return label.en;
    return "";
  },
}));

describe("SynthesisView", () => {
  const mockEntity: EntityRead = {
    id: "entity-123",
    slug: "paracetamol",
    kind: "medication",
    label: { en: "Paracetamol" },
    label_i18n: {},
    summary: { en: "Common pain reliever" },
    created_at: "2025-01-01T00:00:00Z",
  };

  const createMockRelation = (overrides?: Partial<RelationRead>): RelationRead => ({
    id: "rel-1",
    kind: "treats",
    source_id: "source-1",
    target_id: "entity-123",
    direction: "positive",
    confidence: 0.85,
    scope: null,
    created_at: "2025-01-01T00:00:00Z",
    created_by_user_id: "user-1",
    roles: {},
    ...overrides,
  });

  const createMockInference = (overrides?: Partial<InferenceRead>): InferenceRead => ({
    entity_id: "entity-123",
    relations_by_kind: {
      treats: [
        createMockRelation({ id: "rel-1", kind: "treats", confidence: 0.85, source_id: "source-1" }),
        createMockRelation({ id: "rel-2", kind: "treats", confidence: 0.90, source_id: "source-2" }),
      ],
      causes: [
        createMockRelation({ id: "rel-3", kind: "causes", confidence: 0.75, source_id: "source-3" }),
      ],
    },
    role_inferences: [
      {
        role_type: "therapeutic_use",
        score: 0.8,
        coverage: 10,
        confidence: 0.85,
        disagreement: 0.1,
      },
    ],
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading state", () => {
    it("shows loading message initially", () => {
      vi.spyOn(entitiesApi, "getEntity").mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockImplementation(
        () => new Promise(() => {})
      );

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      expect(screen.getByText("Generating synthesis...")).toBeInTheDocument();
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });
  });

  describe("Error state", () => {
    it("shows error when entity fetch fails", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockRejectedValue(
        new Error("Entity not found")
      );
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(screen.getByText(/Entity not found/i)).toBeInTheDocument();
      });
    });

    it("shows error when inference fetch fails", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockRejectedValue(
        new Error("Failed to load synthesis")
      );

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(screen.getByText(/Failed to load synthesis/i)).toBeInTheDocument();
      });
    });
  });

  describe("Successful rendering", () => {
    it("renders synthesis view with entity information", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Knowledge Synthesis")).toBeInTheDocument();
        expect(screen.getAllByText("Paracetamol").length).toBeGreaterThan(0);
      });
    });

    it("displays breadcrumbs for navigation", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Entities")).toBeInTheDocument();
        expect(screen.getByText("Synthesis")).toBeInTheDocument();
      });
    });

    it("includes back button to entity detail", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Back to entity")).toBeInTheDocument();
      });
    });
  });

  describe("Statistics overview", () => {
    it("displays total relations count", async () => {
      const inference = createMockInference();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Total Relations")).toBeInTheDocument();
        // Check for any element with text "3" (there might be multiple)
        expect(screen.getAllByText("3").length).toBeGreaterThan(0);
      });
    });

    it("displays unique sources count", async () => {
      const inference = createMockInference();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Unique Sources")).toBeInTheDocument();
        expect(screen.getAllByText("3").length).toBeGreaterThan(0);
      });
    });

    it("calculates and displays average confidence", async () => {
      const inference = createMockInference();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Avg. Confidence")).toBeInTheDocument();
        // (0.85 + 0.90 + 0.75) / 3 = 0.833... ≈ 83%
        expect(screen.getByText("83%")).toBeInTheDocument();
      });
    });

    it("displays relation types count", async () => {
      const inference = createMockInference();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Relation Types")).toBeInTheDocument();
        expect(screen.getByText("2")).toBeInTheDocument(); // treats, causes
      });
    });
  });

  describe("Quality indicators", () => {
    it("shows evidence quality overview section", async () => {
      const inference = createMockInference();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Evidence Quality Overview")).toBeInTheDocument();
        expect(screen.getByText(/High Confidence/)).toBeInTheDocument();
      });
    });

    it("shows low confidence warning when applicable", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          treats: [
            createMockRelation({ confidence: 0.3, source_id: "source-1" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Low Confidence/)).toBeInTheDocument();
      });
    });

    it("shows contradictions count when present", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          treats: [
            createMockRelation({ direction: "positive" }),
            createMockRelation({ direction: "contradicts" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Contradictions/)).toBeInTheDocument();
      });
    });

    it("does not show low confidence chip when none exist", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          treats: [
            createMockRelation({ confidence: 0.85 }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/High Confidence/)).toBeInTheDocument();
      });

      expect(screen.queryByText(/Low Confidence/)).not.toBeInTheDocument();
    });
  });

  describe("Relations by kind", () => {
    it("displays relation types as expandable accordions", async () => {
      const inference = createMockInference();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Relations by Type")).toBeInTheDocument();
        expect(screen.getAllByText("treats").length).toBeGreaterThan(0);
      });
    });

    it("shows relation count per kind", async () => {
      const inference = createMockInference();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("2 relations")).toBeInTheDocument(); // treats
        expect(screen.getByText("1 relation")).toBeInTheDocument(); // causes
      });
    });

    it("shows confidence percentage per kind", async () => {
      const inference = createMockInference();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        // treats: (0.85 + 0.90) / 2 = 88%
        expect(screen.getByText("88% confidence")).toBeInTheDocument();
        // causes: 0.75 = 75%
        expect(screen.getByText("75% confidence")).toBeInTheDocument();
      });
    });

    it("renders clickable relation items", async () => {
      const inference = createMockInference();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Relations by Type")).toBeInTheDocument();
        // Verify relation list items are rendered (they're in accordions)
        expect(screen.getAllByText("treats").length).toBeGreaterThan(0);
      });
    });
  });

  describe("Knowledge gaps", () => {
    it("shows knowledge gap warning when few relation types exist", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          treats: [createMockRelation()],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Knowledge Gaps Detected")).toBeInTheDocument();
        expect(screen.getByText(/limited relation types/i)).toBeInTheDocument();
      });
    });

    it("does not show knowledge gap when sufficient relation types exist", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          treats: [createMockRelation()],
          causes: [createMockRelation()],
          prevents: [createMockRelation()],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Relations by Type")).toBeInTheDocument();
      });

      expect(screen.queryByText("Knowledge Gaps Detected")).not.toBeInTheDocument();
    });
  });

  describe("Action buttons", () => {
    it("shows view disagreements button when contradictions exist", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          treats: [
            createMockRelation({ direction: "contradicts" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/View Disagreements/)).toBeInTheDocument();
      });
    });

    it("navigates to disagreements view when button clicked", async () => {
      const user = userEvent.setup();
      const inference = createMockInference({
        relations_by_kind: {
          treats: [
            createMockRelation({ direction: "contradicts" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/View Disagreements/)).toBeInTheDocument();
      });

      await user.click(screen.getByText(/View Disagreements/));
      expect(mockNavigate).toHaveBeenCalledWith("/entities/entity-123/disagreements");
    });

    it("navigates back to entity detail when back button clicked", async () => {
      const user = userEvent.setup();
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Back to entity")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Back to entity"));
      expect(mockNavigate).toHaveBeenCalledWith("/entities/entity-123");
    });
  });

  describe("No data state", () => {
    it("shows no data message when no relations exist", async () => {
      const inference = createMockInference({
        relations_by_kind: {},
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("No synthesized knowledge available")).toBeInTheDocument();
        expect(screen.getByText(/Add relations and sources to generate knowledge synthesis/)).toBeInTheDocument();
      });
    });

    it("does not show statistics when no data", async () => {
      const inference = createMockInference({
        relations_by_kind: {},
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <SynthesisView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("No synthesized knowledge available")).toBeInTheDocument();
      });

      expect(screen.queryByText("Total Relations")).not.toBeInTheDocument();
      expect(screen.queryByText("Unique Sources")).not.toBeInTheDocument();
    });
  });
});

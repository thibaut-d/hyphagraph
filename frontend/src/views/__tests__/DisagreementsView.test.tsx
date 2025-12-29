/**
 * Tests for DisagreementsView component.
 *
 * Tests contradictions display, side-by-side evidence comparison,
 * scientific honesty principle, statistics, and navigation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { DisagreementsView } from "../DisagreementsView";
import type { EntityRead } from "../../api/entities";
import type { RelationRead } from "../../types/relation";
import type { InferenceRead } from "../../types/inference";
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

// Mock i18n
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValueOrOptions?: string | { defaultValue?: string; [key: string]: any }) => {
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      if (defaultValueOrOptions && typeof defaultValueOrOptions === "object") {
        let result = defaultValueOrOptions.defaultValue || key;
        // Handle template interpolation like {{value}}
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

describe("DisagreementsView", () => {
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
    entity_id: "entity-123",
    kind: "therapeutic_use",
    direction: "supports",
    source_id: "source-1",
    confidence: 0.85,
    scope: null,
    created_at: "2025-01-01T00:00:00Z",
    ...overrides,
  });

  const createMockInference = (overrides?: Partial<InferenceRead>): InferenceRead => ({
    entity_id: "entity-123",
    relations_by_kind: {
      therapeutic_use: [
        createMockRelation({ id: "rel-1", direction: "supports", confidence: 0.9 }),
        createMockRelation({ id: "rel-2", direction: "contradicts", confidence: 0.7 }),
      ],
    },
    role_inferences: [
      {
        role_type: "therapeutic_use",
        score: 0.5,
        coverage: 10,
        confidence: 0.8,
        disagreement: 0.3,
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
          <DisagreementsView />
        </BrowserRouter>
      );

      expect(screen.getByText("Analyzing contradictions...")).toBeInTheDocument();
    });
  });

  describe("Error state", () => {
    it("shows error message when entity fetch fails", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockRejectedValue(
        new Error("Entity not found")
      );
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(screen.getByText(/Entity not found/i)).toBeInTheDocument();
      });
    });

    it("shows error message when inference fetch fails", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockRejectedValue(
        new Error("Inference not found")
      );

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(screen.getByText("Inference not found")).toBeInTheDocument();
      });
    });
  });

  describe("Successful rendering", () => {
    it("renders disagreements view with breadcrumbs", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.queryByText("Analyzing contradictions...")).not.toBeInTheDocument();
      });

      expect(screen.getByText("Entities")).toBeInTheDocument();
      expect(screen.getAllByText("Paracetamol").length).toBeGreaterThan(0);
      expect(screen.getByText("Disagreements")).toBeInTheDocument();
    });

    it("displays scientific honesty warning", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Contradictory Evidence")).toBeInTheDocument();
      });

      expect(
        screen.getByText(/We never hide contradictions/i)
      ).toBeInTheDocument();
    });
  });

  describe("Statistics display", () => {
    it("shows count of conflicting relation types", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          therapeutic_use: [
            createMockRelation({ id: "rel-1", kind: "therapeutic_use", direction: "supports" }),
            createMockRelation({ id: "rel-2", kind: "therapeutic_use", direction: "contradicts" }),
          ],
          side_effect: [
            createMockRelation({ id: "rel-3", kind: "side_effect", direction: "supports" }),
            createMockRelation({ id: "rel-4", kind: "side_effect", direction: "contradicts" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Conflicting Relation Types")).toBeInTheDocument();
        expect(screen.getAllByText("2").length).toBeGreaterThan(0);
      });
    });

    it("shows total contradiction count", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          therapeutic_use: [
            createMockRelation({ id: "rel-1", direction: "supports" }),
            createMockRelation({ id: "rel-2", direction: "contradicts" }),
            createMockRelation({ id: "rel-3", direction: "contradicts" }),
            createMockRelation({ id: "rel-4", direction: "contradicts" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Total Contradictions")).toBeInTheDocument();
        expect(screen.getByText("3")).toBeInTheDocument();
      });
    });
  });

  describe("Disagreement groups", () => {
    it("displays disagreement groups in accordions", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          therapeutic_use: [
            createMockRelation({ id: "rel-1", kind: "therapeutic_use", direction: "supports" }),
            createMockRelation({ id: "rel-2", kind: "therapeutic_use", direction: "contradicts" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getAllByText("therapeutic_use").length).toBeGreaterThan(0);
      });

      expect(screen.getByText("1 supporting")).toBeInTheDocument();
      expect(screen.getByText("1 contradicting")).toBeInTheDocument();
    });

    it("shows confidence percentage for each group", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          therapeutic_use: [
            createMockRelation({ id: "rel-1", direction: "supports", confidence: 0.9 }),
            createMockRelation({ id: "rel-2", direction: "contradicts", confidence: 0.7 }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        // Average confidence: (0.9 + 0.7) / 2 = 0.8 = 80%
        expect(screen.getByText("80% confidence")).toBeInTheDocument();
      });
    });

    it("displays supporting and contradicting chips", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          therapeutic_use: [
            createMockRelation({
              id: "rel-1",
              kind: "therapeutic_use",
              direction: "supports",
              confidence: 0.9,
              source_id: "source-1",
            }),
            createMockRelation({
              id: "rel-2",
              kind: "therapeutic_use",
              direction: "contradicts",
              confidence: 0.7,
              source_id: "source-2",
            }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("1 supporting")).toBeInTheDocument();
        expect(screen.getByText("1 contradicting")).toBeInTheDocument();
      });
    });

    it("shows multiple disagreement groups", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          therapeutic_use: [
            createMockRelation({ id: "rel-1", kind: "therapeutic_use", direction: "supports" }),
            createMockRelation({ id: "rel-2", kind: "therapeutic_use", direction: "contradicts" }),
          ],
          side_effect: [
            createMockRelation({ id: "rel-3", kind: "side_effect", direction: "supports" }),
            createMockRelation({ id: "rel-4", kind: "side_effect", direction: "contradicts" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getAllByText("therapeutic_use").length).toBeGreaterThan(0);
        expect(screen.getAllByText("side_effect").length).toBeGreaterThan(0);
      });
    });
  });

  describe("Guidance section", () => {
    it("displays guidance on interpreting disagreements", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("How to Interpret Disagreements")).toBeInTheDocument();
      });

      expect(
        screen.getByText(/Contradictions are normal in science/i)
      ).toBeInTheDocument();
    });
  });

  describe("No contradictions state", () => {
    it("shows success message when no contradictions exist", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          therapeutic_use: [
            createMockRelation({ id: "rel-1", direction: "supports" }),
            createMockRelation({ id: "rel-2", direction: "supports" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("No contradictions detected")).toBeInTheDocument();
      });

      expect(
        screen.getByText(/All available evidence for this entity is consistent/i)
      ).toBeInTheDocument();
    });

    it("does not show disagreement groups when no contradictions", async () => {
      const inference = createMockInference({
        relations_by_kind: {
          therapeutic_use: [
            createMockRelation({ id: "rel-1", direction: "supports" }),
          ],
        },
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(inference);

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("No contradictions detected")).toBeInTheDocument();
      });

      expect(screen.queryByText("Contradictions by Relation Type")).not.toBeInTheDocument();
    });
  });

  describe("Navigation actions", () => {
    it("shows view synthesis button", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("View Full Synthesis")).toBeInTheDocument();
      });
    });

    it("shows back to entity button", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(inferencesApi, "getInferenceForEntity").mockResolvedValue(
        createMockInference()
      );

      render(
        <BrowserRouter>
          <DisagreementsView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Back to Entity Detail")).toBeInTheDocument();
      });
    });
  });
});

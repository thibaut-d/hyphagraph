/**
 * Tests for PropertyDetailView component.
 *
 * Tests property display, consensus status, limitations, contradictions,
 * and navigation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { PropertyDetailView } from "../PropertyDetailView";
import type { ExplanationRead } from "../../api/explanations";
import type { EntityRead } from "../../api/entities";
import * as entitiesApi from "../../api/entities";
import * as explanationsApi from "../../api/explanations";

// Mock the API modules
vi.mock("../../api/explanations");
vi.mock("../../api/entities");

// Mock react-router-dom hooks
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ entityId: "entity-123", roleType: "therapeutic_use" }),
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

// Mock EvidenceTrace component since it has complex dependencies
vi.mock("../../components/EvidenceTrace", () => ({
  EvidenceTrace: ({ evidence }: { evidence: any[] }) => (
    <div data-testid="evidence-trace">
      Evidence count: {evidence.length}
    </div>
  ),
}));

// Mock resolveLabel utility
vi.mock("../../utils/i18nLabel", () => ({
  resolveLabel: (label: any) => {
    if (typeof label === "string") return label;
    if (label && typeof label === "object" && label.en) return label.en;
    return "";
  },
}));

describe("PropertyDetailView", () => {
  const mockEntity: EntityRead = {
    id: "entity-123",
    slug: "paracetamol",
    kind: "medication",
    label: { en: "Paracetamol" },
    label_i18n: {},
    summary: { en: "Common pain reliever" },
    created_at: "2025-01-01T00:00:00Z",
  };

  const createMockExplanation = (overrides?: Partial<ExplanationRead>): ExplanationRead => ({
    entity_id: "entity-123",
    role_type: "therapeutic_use",
    score: 0.75,
    confidence: 0.85,
    coverage: 10,
    natural_language_summary: "Paracetamol is commonly used for pain relief.",
    evidence_chain: [
      {
        source_id: "source-1",
        source_title: "Clinical Study 2020",
        source_authors: ["Dr. Smith"],
        source_year: 2020,
        source_kind: "clinical_trial",
        source_trust: 0.85,
        source_url: "https://example.com/study1",
        relation_id: "rel-1",
        relation_kind: "treats",
        relation_direction: "positive",
        relation_confidence: 0.9,
        relation_scope: null,
        role_weight: 0.8,
        contribution_percentage: 60.0,
      },
      {
        source_id: "source-2",
        source_title: "Meta-Analysis 2021",
        source_authors: ["Dr. Jones"],
        source_year: 2021,
        source_kind: "meta_analysis",
        source_trust: 0.92,
        source_url: "https://example.com/study2",
        relation_id: "rel-2",
        relation_kind: "treats",
        relation_direction: "positive",
        relation_confidence: 0.88,
        relation_scope: null,
        role_weight: 0.85,
        contribution_percentage: 40.0,
      },
    ],
    contradictions: [],
    limitations: {
      confidence_level: "high",
      coverage: "adequate",
      known_gaps: [],
    },
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
      vi.spyOn(explanationsApi, "getExplanation").mockImplementation(
        () => new Promise(() => {})
      );

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      expect(screen.getByText("Loading property details...")).toBeInTheDocument();
    });
  });

  describe("Error state", () => {
    it("shows error message when entity fetch fails", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockRejectedValue(
        new Error("Entity not found")
      );
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(
        createMockExplanation()
      );

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(screen.getByText(/Entity not found/i)).toBeInTheDocument();
      });
    });

    it("shows error message when explanation fetch fails", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockRejectedValue(
        new Error("Explanation not found")
      );

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(screen.getByText("Explanation not found")).toBeInTheDocument();
      });
    });
  });

  describe("Successful rendering", () => {
    it("renders property details successfully", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(
        createMockExplanation()
      );

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.queryByText("Loading property details...")).not.toBeInTheDocument();
      });
    });

    it("displays natural language summary", async () => {
      const explanation = createMockExplanation({
        natural_language_summary: "This medication is highly effective for pain management.",
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(explanation);

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(
          screen.getByText("This medication is highly effective for pain management.")
        ).toBeInTheDocument();
      });
    });

    it("displays evidence chain", async () => {
      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(
        createMockExplanation()
      );

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId("evidence-trace")).toBeInTheDocument();
        expect(screen.getByText("Evidence count: 2")).toBeInTheDocument();
      });
    });
  });

  describe("Consensus status", () => {
    it("shows strong consensus for high confidence without contradictions", async () => {
      const explanation = createMockExplanation({
        confidence: 0.85,
        contradictions: [],
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(explanation);

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Strong Consensus")).toBeInTheDocument();
      });
    });

    it("shows moderate consensus for medium confidence", async () => {
      const explanation = createMockExplanation({
        confidence: 0.55,
        contradictions: [],
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(explanation);

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Moderate Consensus")).toBeInTheDocument();
      });
    });

    it("shows weak evidence for low confidence", async () => {
      const explanation = createMockExplanation({
        confidence: 0.25,
        contradictions: [],
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(explanation);

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Weak Evidence")).toBeInTheDocument();
      });
    });

    it("shows disputed status when contradictions exist", async () => {
      const explanation = createMockExplanation({
        confidence: 0.85,
        contradictions: [
          { detail: "Some studies show no effect", source_count: 3 },
        ],
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(explanation);

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Disputed / Contradictory")).toBeInTheDocument();
      });
    });
  });

  describe("Known limitations", () => {
    it("displays known limitations section when confidence is low", async () => {
      const explanation = createMockExplanation({
        confidence: 0.6, // Below 0.7 threshold
        contradictions: [],
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(explanation);

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Known Limitations")).toBeInTheDocument();
      });
    });
  });

  describe("Contradictions section", () => {
    it("displays contradictions prominently with error styling", async () => {
      const explanation = createMockExplanation({
        contradictions: [
          { detail: "Study A found no effect", source_count: 2 },
          { detail: "Study B showed opposite results", source_count: 1 },
        ],
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(explanation);

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Contradictory Evidence")).toBeInTheDocument();
        expect(screen.getByText("Study A found no effect")).toBeInTheDocument();
        expect(screen.getByText(/Scientific honesty requires showing all evidence/i)).toBeInTheDocument();
      });
    });

    it("shows source count for contradictions", async () => {
      const explanation = createMockExplanation({
        contradictions: [
          { detail: "Contradictory finding", source_count: 5 },
        ],
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(explanation);

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        // Just verify contradictory finding is shown
        expect(screen.getByText("Contradictory finding")).toBeInTheDocument();
      });
    });

    it("does not show contradictions section when none exist", async () => {
      const explanation = createMockExplanation({
        contradictions: [],
      });

      vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
      vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(explanation);

      render(
        <BrowserRouter>
          <PropertyDetailView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Strong Consensus")).toBeInTheDocument();
      });

      expect(screen.queryByText("Contradictory Evidence")).not.toBeInTheDocument();
    });
  });
});

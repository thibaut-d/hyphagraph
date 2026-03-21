/**
 * Tests for PropertyDetailView component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { PropertyDetailView } from "../PropertyDetailView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import type { ExplanationRead, SourceContribution } from "../../api/explanations";
import type { EntityRead } from "../../types/entity";
import * as entitiesApi from "../../api/entities";
import * as explanationsApi from "../../api/explanations";

vi.mock("../../api/explanations");
vi.mock("../../api/entities");

const translate = (
  key: string,
  defaultValueOrOptions?: string | { [key: string]: any },
  interpolation?: { [key: string]: any },
) => {
  if (typeof defaultValueOrOptions === "string") {
    let result = defaultValueOrOptions;
    if (interpolation && typeof interpolation === "object") {
      Object.keys(interpolation).forEach((k) => {
        result = result.replace(`{{${k}}}`, String(interpolation[k]));
      });
    }
    return result;
  }
  if (defaultValueOrOptions && typeof defaultValueOrOptions === "object") {
    let result = key;
    const fallback = defaultValueOrOptions.defaultValue;
    if (typeof fallback === "string") {
      result = fallback;
    }
    Object.keys(defaultValueOrOptions).forEach((k) => {
      if (k !== "defaultValue") {
        result = result.replace(`{{${k}}}`, String(defaultValueOrOptions[k]));
      }
    });
    return result;
  }
  return key;
};

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: "entity-123", roleType: "therapeutic_use" }),
  };
});

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: translate,
    i18n: { language: "en" },
  }),
  initReactI18next: { type: '3rdParty', init: () => {} },
}));

vi.mock("../../components/EvidenceTrace", () => ({
  EvidenceTrace: ({ sourceChain }: { sourceChain: SourceContribution[] }) => (
    <div data-testid="evidence-trace">Evidence count: {sourceChain.length}</div>
  ),
}));

const renderWithProviders = () =>
  render(
    <NotificationProvider>
      <BrowserRouter>
        <PropertyDetailView />
      </BrowserRouter>
    </NotificationProvider>,
  );

describe("PropertyDetailView", () => {
  const mockEntity: EntityRead = {
    id: "entity-123",
    slug: "paracetamol",
    summary: { en: "Common pain reliever" },
    created_at: "2025-01-01T00:00:00Z",
  };

  const mockSourceChain: SourceContribution[] = [
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
      relation_direction: "supports",
      relation_confidence: 0.9,
      relation_scope: {},
      role_weight: 0.8,
      contribution_percentage: 60,
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
      relation_direction: "supports",
      relation_confidence: 0.88,
      relation_scope: {},
      role_weight: 0.85,
      contribution_percentage: 40,
    },
  ];

  const createMockExplanation = (overrides?: Partial<ExplanationRead>): ExplanationRead => ({
    entity_id: "entity-123",
    role_type: "therapeutic_use",
    score: 0.75,
    confidence: 0.85,
    disagreement: 0.1,
    summary: "Paracetamol is commonly used for pain relief.",
    confidence_factors: [],
    source_chain: mockSourceChain,
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading message initially", () => {
    vi.spyOn(entitiesApi, "getEntity").mockImplementation(() => new Promise(() => {}));
    vi.spyOn(explanationsApi, "getExplanation").mockImplementation(() => new Promise(() => {}));

    renderWithProviders();

    expect(screen.getByText("Loading property details...")).toBeInTheDocument();
  });

  it("shows error message when entity fetch fails", async () => {
    vi.spyOn(entitiesApi, "getEntity").mockRejectedValue(new Error("Entity not found"));
    vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(createMockExplanation());

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/Entity not found/i)).toBeInTheDocument();
    });
  });

  it("renders summary and evidence chain", async () => {
    vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
    vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(
      createMockExplanation({
        summary: "This medication is highly effective for pain management.",
      }),
    );

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText("This medication is highly effective for pain management.")).toBeInTheDocument();
      expect(screen.getByTestId("evidence-trace")).toBeInTheDocument();
      expect(screen.getByText("Evidence count: 2")).toBeInTheDocument();
    });
  });

  it("shows strong consensus for high confidence without contradictions", async () => {
    vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
    vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(
      createMockExplanation({ confidence: 0.85 }),
    );

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText("Strong Consensus")).toBeInTheDocument();
    });
  });

  it("shows disputed status and contradiction counts", async () => {
    vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
    vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(
      createMockExplanation({
        contradictions: {
          supporting_sources: [mockSourceChain[0]],
          contradicting_sources: [mockSourceChain[1]],
          disagreement_score: 0.52,
        },
      }),
    );

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText("Disputed / Contradictory")).toBeInTheDocument();
      expect(screen.getByText("Contradictory Evidence")).toBeInTheDocument();
      expect(screen.getByText("Supporting: 1")).toBeInTheDocument();
      expect(screen.getByText("Contradicting: 1")).toBeInTheDocument();
    });
  });

  it("displays known limitations when confidence is low", async () => {
    vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
    vi.spyOn(explanationsApi, "getExplanation").mockResolvedValue(
      createMockExplanation({
        confidence: 0.35,
        source_chain: [mockSourceChain[0]],
      }),
    );

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText("Known Limitations")).toBeInTheDocument();
    });
  });
});

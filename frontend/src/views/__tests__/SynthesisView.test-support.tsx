import { render as rtlRender, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import { BrowserRouter } from "react-router-dom";
import { vi } from "vitest";

import { SynthesisView } from "../SynthesisView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import type { EntityRead } from "../../api/entities";
import type { InferenceDetailRead } from "../../types/inference";
import type { RelationRead } from "../../types/relation";
import * as entitiesApi from "../../api/entities";
import * as inferencesApi from "../../api/inferences";

vi.mock("../../api/entities");
vi.mock("../../api/inferences");

export const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: "entity-123" }),
  };
});

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValueOrOptions?: string | { defaultValue?: string; [key: string]: any }) => {
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      if (defaultValueOrOptions && typeof defaultValueOrOptions === "object") {
        let result = defaultValueOrOptions.defaultValue || key;
        Object.keys(defaultValueOrOptions).forEach((field) => {
          if (field !== "defaultValue") {
            result = result.replace(`{{${field}}}`, String(defaultValueOrOptions[field]));
          }
        });
        return result;
      }
      return key;
    },
    i18n: { language: "en" },
  }),
  initReactI18next: { type: '3rdParty', init: () => {} },
}));

vi.mock("../../utils/i18nLabel", () => ({
  resolveLabel: (label: any) => {
    if (typeof label === "string") return label;
    if (label && typeof label === "object" && label.en) return label.en;
    return "";
  },
}));

export function renderWithNotifications(ui: ReactElement): RenderResult {
  return rtlRender(<NotificationProvider>{ui}</NotificationProvider>);
}

export function renderSynthesisView() {
  return renderWithNotifications(
    <BrowserRouter>
      <SynthesisView />
    </BrowserRouter>
  );
}

export const mockEntity: EntityRead = {
  id: "entity-123",
  slug: "paracetamol",
  summary: { en: "Common pain reliever" },
  created_at: "2025-01-01T00:00:00Z",
};

export function createMockRelation(overrides?: Partial<RelationRead>): RelationRead {
  return {
    id: "rel-1",
    kind: "treats",
    source_id: "source-1",
    direction: "positive",
    confidence: 0.85,
    scope: null,
    created_at: "2025-01-01T00:00:00Z",
    roles: [],
    ...overrides,
  };
}

function buildRelationKindSummaries(relationsByKind: Record<string, RelationRead[]>) {
  return Object.entries(relationsByKind).map(([kind, relations]) => {
    const confidenceValues = relations
      .map((relation) => relation.confidence ?? 0)
      .filter((value) => value !== null);
    const supportingCount = relations.filter((relation) => relation.direction === "supports").length;
    const contradictingCount = relations.filter((relation) => relation.direction === "contradicts").length;
    return {
      kind,
      relation_count: relations.length,
      average_confidence: confidenceValues.length
        ? confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length
        : 0,
      supporting_count: supportingCount,
      contradicting_count: contradictingCount,
      neutral_count: relations.length - supportingCount - contradictingCount,
    };
  });
}

function buildStats(relationsByKind: Record<string, RelationRead[]>) {
  const relations = Object.values(relationsByKind).flat();
  const confidenceValues = relations
    .map((relation) => relation.confidence)
    .filter((value): value is number => value !== undefined && value !== null);

  return {
    total_relations: relations.length,
    unique_sources_count: new Set(
      relations
        .map((relation) => relation.source_id)
        .filter((sourceId): sourceId is string => Boolean(sourceId)),
    ).size,
    average_confidence: confidenceValues.length
      ? confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length
      : 0,
    confidence_count: confidenceValues.length,
    high_confidence_count: confidenceValues.filter((value) => value > 0.7).length,
    low_confidence_count: confidenceValues.filter((value) => value < 0.4).length,
    contradiction_count: relations.filter((relation) => relation.direction === "contradicts").length,
    relation_type_count: Object.keys(relationsByKind).length,
  };
}

export function createMockInference(overrides?: Partial<InferenceDetailRead>): InferenceDetailRead {
  const baseRelationsByKind = {
    treats: [
      createMockRelation({ id: "rel-1", kind: "treats", confidence: 0.85, source_id: "source-1" }),
      createMockRelation({ id: "rel-2", kind: "treats", confidence: 0.9, source_id: "source-2" }),
    ],
    causes: [createMockRelation({ id: "rel-3", kind: "causes", confidence: 0.75, source_id: "source-3" })],
  };
  const relationsByKind = overrides?.relations_by_kind ?? baseRelationsByKind;

  return {
    entity_id: "entity-123",
    relations_by_kind: relationsByKind,
    role_inferences: [
      {
        role_type: "therapeutic_use",
        score: 0.8,
        coverage: 10,
        confidence: 0.85,
        disagreement: 0.1,
      },
    ],
    stats: buildStats(relationsByKind),
    relation_kind_summaries: buildRelationKindSummaries(relationsByKind),
    evidence_items: [],
    disagreement_groups: [],
    ...overrides,
  };
}

export function mockSuccessfulSynthesisData(inference = createMockInference()) {
  vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
  vi.spyOn(inferencesApi, "getInferenceDetailForEntity").mockResolvedValue(inference);
}

export function mockSynthesisEntityPending() {
  vi.spyOn(entitiesApi, "getEntity").mockImplementation(() => new Promise(() => {}));
}

export function mockSynthesisEntityRejected(error: unknown) {
  vi.spyOn(entitiesApi, "getEntity").mockRejectedValue(error);
}

export function mockSynthesisEntityResolved(entity = mockEntity) {
  vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(entity);
}

export function mockSynthesisInferencePending() {
  vi.spyOn(inferencesApi, "getInferenceDetailForEntity").mockImplementation(() => new Promise(() => {}));
}

export function mockSynthesisInferenceRejected(error: unknown) {
  vi.spyOn(inferencesApi, "getInferenceDetailForEntity").mockRejectedValue(error);
}

export function mockSynthesisInferenceResolved(inference = createMockInference()) {
  vi.spyOn(inferencesApi, "getInferenceDetailForEntity").mockResolvedValue(inference);
}

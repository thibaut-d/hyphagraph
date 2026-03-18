import { render as rtlRender, type RenderResult, screen, fireEvent } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { EvidenceView } from "../EvidenceView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import type { EntityRead } from "../../types/entity";
import type { RelationRead } from "../../types/relation";
import type { SourceRead } from "../../types/source";
import type { EvidenceItemRead, InferenceDetailRead } from "../../types/inference";
import * as entitiesApi from "../../api/entities";
import * as inferencesApi from "../../api/inferences";
import * as sourcesApi from "../../api/sources";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      if (key === "evidence.count") {
        const count = params?.count ?? 0;
        return `${count} evidence items`;
      }
      if (params?.defaultValue) {
        let result = params.defaultValue;
        return result.replace(/\{\{(\w+)\}\}/g, (_: string, match: string) =>
          String(params[match] ?? "")
        );
      }
      if (params && typeof params === "object") {
        return key.replace(/\{\{(\w+)\}\}/g, (_, match) => params[match] || "");
      }
      return key;
    },
    i18n: { language: "en" },
  }),
}));

export function renderWithNotifications(ui: ReactElement): RenderResult {
  return rtlRender(<NotificationProvider>{ui}</NotificationProvider>);
}

export const mockEntity: EntityRead = {
  id: "entity-1",
  slug: "paracetamol",
  label: "Paracetamol",
  label_i18n: { en: "Paracetamol" },
  kind: "substance",
  ui_category_id: "drug",
  summary: { en: "A common pain reliever" },
  created_at: "2025-01-01T00:00:00Z",
};

export const mockRelations: RelationRead[] = [
  {
    id: "rel-1",
    source_id: "source-1",
    kind: "treats",
    direction: "supports",
    confidence: 0.8,
    roles: [
      { entity_id: "entity-1", role_type: "agent", entity_slug: "paracetamol" },
      { entity_id: "entity-1", role_type: "patient", entity_slug: "paracetamol" },
    ],
    notes: "Strong evidence",
  },
  {
    id: "rel-2",
    source_id: "source-2",
    kind: "causes_side_effect",
    direction: "contradicts",
    confidence: 0.6,
    roles: [
      { entity_id: "entity-1", role_type: "agent", entity_slug: "paracetamol" },
      { entity_id: "entity-3", role_type: "outcome", entity_slug: "nausea" },
    ],
  },
  {
    id: "rel-3",
    source_id: "source-3",
    kind: "treats",
    direction: "supports",
    confidence: 0.9,
    roles: [{ entity_id: "entity-1", role_type: "agent", entity_slug: "paracetamol" }],
  },
];

export const mockSources: SourceRead[] = [
  {
    id: "source-1",
    title: "Clinical Trial A",
    authors: ["Smith, J.", "Doe, A."],
    year: 2020,
    kind: "clinical_trial",
    origin: "journal",
    trust_level: 0.9,
    created_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "source-2",
    title: "Observational Study B",
    authors: ["Johnson, K."],
    year: 2019,
    kind: "observational_study",
    origin: "journal",
    trust_level: 0.7,
    created_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "source-3",
    title: "Meta-Analysis C",
    authors: ["Brown, L.", "White, M.", "Green, P."],
    year: 2021,
    kind: "meta_analysis",
    origin: "journal",
    trust_level: 0.95,
    created_at: "2025-01-01T00:00:00Z",
  },
];

export const mockInference: InferenceDetailRead = {
  entity_id: "entity-1",
  relations_by_kind: {
    treats: [mockRelations[0], mockRelations[2]],
    causes_side_effect: [mockRelations[1]],
  },
  stats: {
    total_relations: 3,
    unique_sources_count: 3,
    average_confidence: 0.7666666667,
    confidence_count: 3,
    high_confidence_count: 2,
    low_confidence_count: 0,
    contradiction_count: 1,
    relation_type_count: 2,
  },
  relation_kind_summaries: [
    {
      kind: "treats",
      relation_count: 2,
      average_confidence: 0.85,
      supporting_count: 2,
      contradicting_count: 0,
      neutral_count: 0,
    },
    {
      kind: "causes_side_effect",
      relation_count: 1,
      average_confidence: 0.6,
      supporting_count: 0,
      contradicting_count: 1,
      neutral_count: 0,
    },
  ],
  evidence_items: mockRelations.map((relation): EvidenceItemRead => ({
    ...relation,
    source: mockSources.find((source) => source.id === relation.source_id) ?? null,
  })),
  disagreement_groups: [],
};

export function renderEvidenceView(initialEntry = "/entities/entity-1/evidence") {
  return renderWithNotifications(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/entities/:id/evidence" element={<EvidenceView />} />
        <Route path="/entities/:id/properties/:roleType/evidence" element={<EvidenceView />} />
      </Routes>
    </MemoryRouter>
  );
}

export function mockSuccessfulEvidenceData() {
  vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(mockEntity);
  vi.spyOn(inferencesApi, "getInferenceDetailForEntity").mockResolvedValue(mockInference);
  vi.spyOn(sourcesApi, "getSource").mockImplementation((id: string) => {
    const source = mockSources.find((item) => item.id === id);
    return source ? Promise.resolve(source) : Promise.reject(new Error("Source not found"));
  });
}

export function mockEvidenceEntityPending() {
  vi.spyOn(entitiesApi, "getEntity").mockImplementation(() => new Promise(() => {}));
}

export function mockEvidenceEntityRejected(error: unknown) {
  vi.spyOn(entitiesApi, "getEntity").mockRejectedValue(error);
}

export function mockEvidenceEntityResolved(entity = mockEntity) {
  vi.spyOn(entitiesApi, "getEntity").mockResolvedValue(entity);
}

export function mockEvidenceInferencePending() {
  vi.spyOn(inferencesApi, "getInferenceDetailForEntity").mockImplementation(() => new Promise(() => {}));
}

export function mockEvidenceInferenceResolved(inference: Partial<InferenceDetailRead>) {
  vi.spyOn(inferencesApi, "getInferenceDetailForEntity").mockResolvedValue(inference as InferenceDetailRead);
}

export function clickSortableHeader(label: string) {
  const header = screen.getByText(label).closest("th");
  const sortButton = header?.querySelector('[role="button"]');
  if (sortButton) {
    fireEvent.click(sortButton);
  }
}

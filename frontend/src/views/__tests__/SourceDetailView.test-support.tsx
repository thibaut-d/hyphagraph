import { render, type RenderResult } from "@testing-library/react";
import { BrowserRouter, Route, Routes } from "react-router";
import { vi } from "vitest";

import { SourceDetailView } from "../SourceDetailView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import type { SourceRead } from "../../types/source";
import type { RelationRead } from "../../types/relation";
import * as sourcesApi from "../../api/sources";
import * as relationsApi from "../../api/relations";

vi.mock("../../api/sources", () => ({
  getSource: vi.fn(),
  deleteSource: vi.fn(),
}));

vi.mock("../../api/relations", () => ({
  listRelationsBySource: vi.fn(),
  deleteRelation: vi.fn(),
}));

vi.mock("../../utils/cacheUtils", () => ({
  invalidateSourceFilterCache: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValueOrOptions?: string | { defaultValue?: string }) => {
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      return defaultValueOrOptions?.defaultValue || key;
    },
  }),
  initReactI18next: { type: '3rdParty', init: () => {} },
}));

export const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

export const getSource = sourcesApi.getSource as any;
export const deleteSource = sourcesApi.deleteSource as any;
export const listRelationsBySource = relationsApi.listRelationsBySource as any;
export const deleteRelation = relationsApi.deleteRelation as any;

export const mockSource: SourceRead = {
  id: "123e4567-e89b-12d3-a456-426614174000",
  kind: "study",
  title: "Test Study on Aspirin",
  year: 2020,
  trust_level: 0.85,
  url: "https://example.com/study",
  authors: ["Author A", "Author B"],
  created_at: new Date().toISOString(),
  status: "confirmed",
};

export const mockRelations: RelationRead[] = [
  {
    id: "rel-1",
    source_id: "123e4567-e89b-12d3-a456-426614174000",
    kind: "effect",
    direction: "positive",
    confidence: 0.9,
    roles: [{ id: "role-1", relation_revision_id: "rev-1", role_type: "drug", entity_id: "entity-1" }],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    status: "confirmed",
  },
  {
    id: "rel-2",
    source_id: "123e4567-e89b-12d3-a456-426614174000",
    kind: "mechanism",
    direction: "supports",
    confidence: 0.8,
    roles: [{ id: "role-2", relation_revision_id: "rev-2", role_type: "drug", entity_id: "entity-2" }],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    status: "confirmed",
  },
];

export function renderSourceDetailView(sourceId: string): RenderResult {
  return render(
    <NotificationProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/sources/:id" element={<SourceDetailView />} />
        </Routes>
      </BrowserRouter>
    </NotificationProvider>,
    {
      wrapper: ({ children }) => {
        window.history.pushState({}, "", `/sources/${sourceId}`);
        return <>{children}</>;
      },
    }
  );
}

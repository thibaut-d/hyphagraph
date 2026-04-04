import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { RelationDetailView } from "../RelationDetailView";
import * as relationsApi from "../../api/relations";
import * as sourcesApi from "../../api/sources";

vi.mock("../../api/relations");
vi.mock("../../api/sources");
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (_key: string, defaultValue?: string) => defaultValue ?? _key,
  }),
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

const showError = vi.fn();

vi.mock("../../notifications/NotificationContext", () => ({
  NotificationProvider: ({ children }: { children: ReactNode }) => children,
  useNotification: () => ({
    showError,
    showInfo: vi.fn(),
    showSuccess: vi.fn(),
    showWarning: vi.fn(),
  }),
}));

describe("RelationDetailView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders relation meaning, roles, and source traceability", async () => {
    vi.spyOn(relationsApi, "getRelation").mockResolvedValue({
      id: "rel-1",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
      source_id: "src-1",
      kind: "treats",
      direction: "supports",
      confidence: 0.82,
      scope: { population: "adults" },
      notes: "Explicitly stated in the abstract.",
      created_with_llm: null,
      status: "confirmed",
      llm_review_status: null,
      roles: [
        {
          id: "role-1",
          relation_revision_id: "rev-1",
          entity_id: "entity-1",
          role_type: "subject",
          entity_slug: "aspirin",
        },
        {
          id: "role-2",
          relation_revision_id: "rev-1",
          entity_id: "entity-2",
          role_type: "object",
          entity_slug: "headache",
        },
      ],
    });

    vi.spyOn(sourcesApi, "getSource").mockResolvedValue({
      id: "src-1",
      created_at: "2026-01-01T00:00:00Z",
      kind: "study",
      title: "Aspirin for headache relief",
      authors: ["Smith", "Jones"],
      year: 2024,
      origin: null,
      url: "https://example.com/source",
      trust_level: 0.9,
      summary: { en: "Clinical study summary" },
      source_metadata: null,
      created_with_llm: null,
      created_by_user_id: null,
      status: "confirmed",
      llm_review_status: null,
      document_format: null,
      document_file_name: null,
      document_extracted_at: null,
    });

    render(
      <MemoryRouter initialEntries={["/relations/rel-1"]}>
        <Routes>
          <Route path="/relations/:id" element={<RelationDetailView />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "treats" })).toBeInTheDocument();
    });

    expect(screen.getByText("aspirin • headache")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Aspirin for headache relief" }).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("aspirin")).toBeInTheDocument();
    expect(screen.getByText("headache")).toBeInTheDocument();
    expect(screen.getByText("Explicitly stated in the abstract.")).toBeInTheDocument();
    expect(screen.getByText(/Document-grounded relation/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View source" })).toHaveAttribute("href", "/sources/src-1");
    expect(screen.getByRole("link", { name: "Edit" })).toHaveAttribute("href", "/relations/rel-1/edit");
    expect(screen.getByRole("link", { name: "aspirin" })).toHaveAttribute("href", "/entities/entity-1");
    expect(screen.getByText(/Relation ID:/)).toBeInTheDocument();
  });
});

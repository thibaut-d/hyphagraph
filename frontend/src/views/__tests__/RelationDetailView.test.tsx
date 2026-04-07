import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { RelationDetailView } from "../RelationDetailView";
import * as relationsApi from "../../api/relations";
import * as sourcesApi from "../../api/sources";

vi.mock("../../api/relations");
vi.mock("../../api/sources");
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (
      key: string,
      defaultValueOrOptions?: string | Record<string, unknown>,
      interpolationOptions?: Record<string, unknown>,
    ) => {
      if (key === "relation.llm_model" && interpolationOptions) {
        return `Model: ${interpolationOptions.value as string}`;
      }
      if (key === "relation.llm_review_status" && interpolationOptions) {
        return `Review: ${interpolationOptions.value as string}`;
      }
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      return key;
    },
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
    expect(screen.getByRole("link", { name: "aspirin" })).toHaveAttribute("href", "/entities/aspirin");
    expect(screen.getByText(/Relation ID:/)).toBeInTheDocument();
  });

  it("shows llm provenance and deletes from the detail page", async () => {
    vi.spyOn(relationsApi, "getRelation").mockResolvedValue({
      id: "rel-2",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
      source_id: "src-2",
      kind: "causes",
      direction: "contradicts",
      confidence: 0.4,
      scope: null,
      notes: null,
      created_with_llm: "gpt-5.4",
      status: "confirmed",
      llm_review_status: "pending_review",
      roles: [],
    });
    vi.spyOn(relationsApi, "deleteRelation").mockResolvedValue();
    vi.spyOn(sourcesApi, "getSource").mockResolvedValue({
      id: "src-2",
      created_at: "2026-01-01T00:00:00Z",
      kind: "study",
      title: "Conflicting study",
      authors: [],
      year: 2025,
      origin: null,
      url: null,
      trust_level: 0.4,
      summary: null,
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
      <MemoryRouter initialEntries={["/relations/rel-2"]}>
        <Routes>
          <Route path="/relations" element={<div>Relations list</div>} />
          <Route path="/relations/:id" element={<RelationDetailView />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/gpt-5\.4/)).toBeInTheDocument();
    });

    expect(screen.getByText(/pending_review/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(screen.getByText("Delete Relation")).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Delete" }).at(-1)!);

    await waitFor(() => {
      expect(relationsApi.deleteRelation).toHaveBeenCalledWith("rel-2");
    });

    await waitFor(() => {
      expect(screen.getByText("Relations list")).toBeInTheDocument();
    });
  });
});

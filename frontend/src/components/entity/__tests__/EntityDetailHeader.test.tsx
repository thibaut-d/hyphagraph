import { useEffect } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { EntityDetailHeader } from "../EntityDetailHeader";
import type { EntityTermRead } from "../../../api/entityTerms";

const mockTerms: EntityTermRead[] = [];

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback || _key,
    i18n: { language: "fr" },
  }),
}));

vi.mock("../../EntityTermsDisplay", () => ({
  EntityTermsDisplay: ({
    onTermsLoaded,
  }: {
    onTermsLoaded?: (terms: EntityTermRead[]) => void;
  }) => {
    useEffect(() => {
      onTermsLoaded?.(mockTerms);
    }, [onTermsLoaded]);
    return <div>Terms</div>;
  },
}));

describe("EntityDetailHeader", () => {
  it("prefers the current-language display name over an international display name", () => {
    mockTerms.splice(
      0,
      mockTerms.length,
      {
        id: "term-intl",
        entity_id: "entity-1",
        term: "Paracetamol",
        language: null,
        display_order: 0,
        is_display_name: true,
        term_kind: "alias",
        created_at: "2026-04-06T00:00:00Z",
      },
      {
        id: "term-fr",
        entity_id: "entity-1",
        term: "Paracétamol",
        language: "fr",
        display_order: 1,
        is_display_name: true,
        term_kind: "alias",
        created_at: "2026-04-06T00:00:00Z",
      },
    );

    render(
      <MemoryRouter>
        <EntityDetailHeader
          entity={{
            id: "entity-1",
            slug: "paracetamol",
            summary: { en: "Pain reliever", fr: "Antalgique" },
            status: "confirmed",
            created_at: "2026-04-06T00:00:00Z",
            updated_at: "2026-04-06T00:00:00Z",
          }}
          onDeleteClick={() => {}}
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Paracétamol" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Paracetamol" })).not.toBeInTheDocument();
    expect(screen.getByText("Antalgique")).toBeInTheDocument();
    expect(screen.queryByText("Pain reliever")).not.toBeInTheDocument();
  });

  it("falls back to the current language display name when no international name exists", () => {
    mockTerms.splice(
      0,
      mockTerms.length,
      {
        id: "term-fr",
        entity_id: "entity-1",
        term: "Paracétamol",
        language: "fr",
        display_order: 1,
        is_display_name: true,
        term_kind: "alias",
        created_at: "2026-04-06T00:00:00Z",
      },
    );

    render(
      <MemoryRouter>
        <EntityDetailHeader
          entity={{
            id: "entity-1",
            slug: "paracetamol",
            summary: { en: "Pain reliever" },
            status: "confirmed",
            created_at: "2026-04-06T00:00:00Z",
            updated_at: "2026-04-06T00:00:00Z",
          }}
          onDeleteClick={() => {}}
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Paracétamol" })).toBeInTheDocument();
  });

  it("falls back to the English summary when no current-language summary exists", () => {
    mockTerms.splice(0, mockTerms.length);

    render(
      <MemoryRouter>
        <EntityDetailHeader
          entity={{
            id: "entity-1",
            slug: "paracetamol",
            summary: { en: "Pain reliever" },
            status: "confirmed",
            created_at: "2026-04-06T00:00:00Z",
            updated_at: "2026-04-06T00:00:00Z",
          }}
          onDeleteClick={() => {}}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Pain reliever")).toBeInTheDocument();
  });
});

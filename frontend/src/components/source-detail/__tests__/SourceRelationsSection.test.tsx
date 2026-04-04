import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { SourceRelationsSection } from "../SourceRelationsSection";
import type { RelationRead } from "../../../types/relation";

function makeRelation(overrides: Partial<RelationRead> = {}): RelationRead {
  return {
    id: "relation-1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    source_id: "source-1",
    kind: "treats",
    direction: "supports",
    confidence: 0.8,
    scope: null,
    notes: null,
    created_with_llm: null,
    status: "confirmed",
    llm_review_status: null,
    roles: [
      {
        id: "role-1",
        relation_revision_id: "revision-1",
        entity_id: "entity-1",
        entity_slug: "aspirin",
        role_type: "subject",
      },
    ],
    ...overrides,
  };
}

describe("SourceRelationsSection", () => {
  it("links relation rows to the relation detail page", () => {
    render(
      <MemoryRouter>
        <SourceRelationsSection
          relations={[makeRelation()]}
          relationsError={null}
          onDeleteRelation={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "treats" })).toHaveAttribute(
      "href",
      "/relations/relation-1",
    );
  });

  it("shows supporting statement context when a relation is highlighted", () => {
    render(
      <MemoryRouter>
        <SourceRelationsSection
          relations={[makeRelation({ notes: "A highlighted passage from the source." })]}
          relationsError={null}
          highlightedRelationId="relation-1"
          onDeleteRelation={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Requested from evidence trace")).toBeInTheDocument();
    expect(screen.getByText("A highlighted passage from the source.")).toBeInTheDocument();
  });

  it("renders entity-first role labels with a readable role caption", () => {
    render(
      <MemoryRouter>
        <SourceRelationsSection
          relations={[
            makeRelation({
              roles: [
                {
                  id: "role-1",
                  relation_revision_id: "revision-1",
                  entity_id: "entity-1",
                  entity_slug: "aspirin",
                  role_type: "primary_agent",
                },
                {
                  id: "role-2",
                  relation_revision_id: "revision-1",
                  entity_id: "entity-2",
                  role_type: "target",
                },
              ],
            }),
          ]}
          relationsError={null}
          onDeleteRelation={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "aspirin" })).toHaveAttribute(
      "href",
      "/entities/entity-1",
    );
    expect(screen.getByRole("link", { name: "entity-2" })).toHaveAttribute(
      "href",
      "/entities/entity-2",
    );
    expect(screen.getByText("(Primary Agent)")).toBeInTheDocument();
    expect(screen.getByText("(Target)")).toBeInTheDocument();
  });

  it("shows summary counts, filter chips, and expandable kind groups", () => {
    render(
      <MemoryRouter>
        <SourceRelationsSection
          relations={[
            makeRelation({ id: "relation-1", kind: "treats", direction: "supports" }),
            makeRelation({ id: "relation-2", kind: "treats", direction: "contradicts", roles: [{ id: "role-2", relation_revision_id: "revision-2", entity_id: "entity-2", entity_slug: "ibuprofen", role_type: "subject" }] }),
            makeRelation({ id: "relation-3", kind: "prevents", direction: "neutral", roles: [{ id: "role-3", relation_revision_id: "revision-3", entity_id: "entity-3", entity_slug: "fever", role_type: "target" }] }),
          ]}
          relationsError={null}
          onDeleteRelation={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getAllByText("1 Supports").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("1 Contradicts").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("1 Neutral").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Filter relations")).toBeInTheDocument();
    expect(screen.getAllByText("prevents").length).toBeGreaterThanOrEqual(1);

    fireEvent.click(screen.getByRole("button", { name: "Contradicts" }));

    expect(screen.getByText("ibuprofen")).toBeInTheDocument();
    expect(screen.queryByText("fever")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "All" }));
    const preventsGroupToggle = screen.getByRole("button", { name: /prevents/i });
    fireEvent.click(preventsGroupToggle);

    expect(preventsGroupToggle).toHaveAttribute("aria-expanded", "false");
  });
});

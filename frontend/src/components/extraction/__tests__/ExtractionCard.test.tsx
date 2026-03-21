/**
 * Tests for ExtractionCard component.
 *
 * Tests badge rendering (type chip, status chip, score chip, flags),
 * approve/reject actions, and materialization links.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ExtractionCard } from "../ExtractionCard";
import type { StagedExtractionRead } from "../../../api/extractionReview";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts) {
        return Object.entries(opts).reduce(
          (s, [k, v]) => s.replace(`{{${k}}}`, String(v)),
          key
        );
      }
      return key;
    },
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual };
});

function makeExtraction(overrides: Partial<StagedExtractionRead> = {}): StagedExtractionRead {
  return {
    id: "ext-1",
    extraction_type: "entity",
    status: "pending",
    source_id: "src-1",
    extraction_data: {
      slug: "aspirin",
      category: "drug",
      summary: "A common analgesic",
      text_span: "aspirin",
    } as unknown as StagedExtractionRead["extraction_data"],
    validation_score: 0.75,
    validation_flags: [],
    auto_commit_eligible: false,
    llm_model: "gpt-4",
    llm_provider: "openai",
    created_at: "2026-01-01T00:00:00Z",
    reviewed_at: undefined,
    review_notes: undefined,
    materialized_entity_id: undefined,
    materialized_relation_id: undefined,
    confidence_adjustment: 1.0,
    ...overrides,
  };
}

function renderCard(extraction: StagedExtractionRead, opts?: {
  isSelected?: boolean;
  onToggleSelect?: () => void;
  onApprove?: () => void;
  onReject?: () => void;
}) {
  const props = {
    extraction,
    isSelected: opts?.isSelected ?? false,
    onToggleSelect: opts?.onToggleSelect ?? vi.fn(),
    onApprove: opts?.onApprove ?? vi.fn(),
    onReject: opts?.onReject ?? vi.fn(),
  };
  return render(
    <MemoryRouter>
      <ExtractionCard {...props} />
    </MemoryRouter>
  );
}

describe("ExtractionCard", () => {
  it("renders entity title (slug)", () => {
    renderCard(makeExtraction());
    expect(screen.getByText("aspirin")).toBeInTheDocument();
  });

  it("renders extraction type chip", () => {
    renderCard(makeExtraction({ extraction_type: "entity" }));
    expect(screen.getByText("entity")).toBeInTheDocument();
  });

  it("renders relation type as title for relation extractions", () => {
    renderCard(
      makeExtraction({
        extraction_type: "relation",
        extraction_data: {
          relation_type: "treats",
          roles: [],
          confidence: "high",
          text_span: "aspirin treats pain",
        } as unknown as StagedExtractionRead["extraction_data"],
      })
    );
    expect(screen.getByText("treats")).toBeInTheDocument();
  });

  it("renders pending status chip", () => {
    renderCard(makeExtraction({ status: "pending" }));
    expect(screen.getByText("extraction_card.status_pending")).toBeInTheDocument();
  });

  it("renders auto_verified status chip", () => {
    renderCard(makeExtraction({ status: "auto_verified" }));
    expect(screen.getByText("extraction_card.status_auto_staged")).toBeInTheDocument();
  });

  it("renders approved status chip", () => {
    renderCard(makeExtraction({ status: "approved" }));
    expect(screen.getByText("extraction_card.status_approved")).toBeInTheDocument();
  });

  it("renders rejected status chip", () => {
    renderCard(makeExtraction({ status: "rejected" }));
    expect(screen.getByText("extraction_card.status_rejected")).toBeInTheDocument();
  });

  it("renders validation score chip", () => {
    renderCard(makeExtraction({ validation_score: 0.85 }));
    expect(screen.getByText("extraction_card.validation_score")).toBeInTheDocument();
  });

  it("renders flags chip when flags are present", () => {
    renderCard(makeExtraction({ validation_flags: ["low_confidence", "no_match"] }));
    expect(screen.getByText("2 flags")).toBeInTheDocument();
  });

  it("does not render flags chip when no flags", () => {
    renderCard(makeExtraction({ validation_flags: [] }));
    expect(screen.queryByText(/flags/)).not.toBeInTheDocument();
  });

  it("renders approve and reject buttons", () => {
    renderCard(makeExtraction());
    expect(screen.getByText("extraction_card.approve")).toBeInTheDocument();
    expect(screen.getByText("extraction_card.reject")).toBeInTheDocument();
  });

  it("calls onApprove when Approve is clicked", () => {
    const onApprove = vi.fn();
    renderCard(makeExtraction(), { onApprove });
    fireEvent.click(screen.getByText("extraction_card.approve"));
    expect(onApprove).toHaveBeenCalledOnce();
  });

  it("calls onReject when Reject is clicked", () => {
    const onReject = vi.fn();
    renderCard(makeExtraction(), { onReject });
    fireEvent.click(screen.getByText("extraction_card.reject"));
    expect(onReject).toHaveBeenCalledOnce();
  });

  it("calls onToggleSelect when checkbox is clicked", () => {
    const onToggleSelect = vi.fn();
    renderCard(makeExtraction(), { onToggleSelect });
    fireEvent.click(screen.getByRole("checkbox"));
    expect(onToggleSelect).toHaveBeenCalledOnce();
  });

  it("renders View Entity link when materialized_entity_id is set", () => {
    renderCard(makeExtraction({ materialized_entity_id: "entity-abc" }));
    const link = screen.getByText("extraction_card.view_entity");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "/entities/entity-abc");
  });

  it("does not render View Entity link without materialized_entity_id", () => {
    renderCard(makeExtraction({ materialized_entity_id: undefined }));
    expect(screen.queryByText("extraction_card.view_entity")).not.toBeInTheDocument();
  });

  it("renders View Relation link when materialized_relation_id is set", () => {
    renderCard(makeExtraction({ materialized_relation_id: "relation-xyz" }));
    const link = screen.getByText("extraction_card.view_relation");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "/relations/relation-xyz");
  });

  it("does not render View Relation link without materialized_relation_id", () => {
    renderCard(makeExtraction({ materialized_relation_id: undefined }));
    expect(screen.queryByText("extraction_card.view_relation")).not.toBeInTheDocument();
  });

  it("shows validation flags list when flags exist", () => {
    renderCard(makeExtraction({ validation_flags: ["duplicate_entity"] }));
    expect(screen.getByText("duplicate_entity")).toBeInTheDocument();
  });

  it("reflects checked state via checkbox", () => {
    renderCard(makeExtraction(), { isSelected: true });
    const checkbox = screen.getByRole("checkbox") as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });
});

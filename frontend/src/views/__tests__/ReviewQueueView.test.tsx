import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ReviewQueueView } from "../ReviewQueueView";
import * as reviewApi from "../../api/extractionReview";

vi.mock("../../api/extractionReview");

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (
      key: string,
      defaultValueOrOptions?: string | { defaultValue?: string; [key: string]: unknown },
    ) => {
      if (typeof defaultValueOrOptions === "string") {
        return defaultValueOrOptions;
      }
      if (defaultValueOrOptions && typeof defaultValueOrOptions === "object") {
        let result = defaultValueOrOptions.defaultValue || key;
        Object.entries(defaultValueOrOptions).forEach(([field, value]) => {
          if (field !== "defaultValue") {
            result = result.replace(`{{${field}}}`, String(value));
          }
        });
        return result;
      }
      return key;
    },
  }),
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

vi.mock("../../components/review/LlmDraftsPanel", () => ({
  LlmDraftsPanel: () => <div>Draft panel content</div>,
}));

vi.mock("../../notifications/NotificationContext", () => ({
  useNotification: () => ({
    showError: vi.fn(),
    showSuccess: vi.fn(),
    showWarning: vi.fn(),
    showInfo: vi.fn(),
  }),
}));

const mockStats = {
  total_pending: 5,
  total_approved: 0,
  total_rejected: 0,
  total_auto_verified: 2,
  pending_entities: 3,
  pending_relations: 2,
  pending_claims: 0,
  avg_validation_score: 0.82,
  high_confidence_count: 0,
  flagged_count: 1,
};

function makeExtraction(overrides: Partial<reviewApi.StagedExtractionRead> = {}): reviewApi.StagedExtractionRead {
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
    } as unknown as reviewApi.StagedExtractionData,
    validation_score: 0.85,
    validation_flags: [],
    auto_commit_eligible: false,
    auto_approved: false,
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

function renderView() {
  return render(
    <MemoryRouter>
      <ReviewQueueView />
    </MemoryRouter>,
  );
}

describe("ReviewQueueView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(reviewApi.getReviewStats).mockResolvedValue(mockStats);
    vi.mocked(reviewApi.listPendingExtractions).mockResolvedValue({
      extractions: [makeExtraction()],
      total: 1,
      page: 1,
      page_size: 20,
      has_more: false,
    });
  });

  it("renders the staged extraction queue with identity, summary, filters, batch tools, and items sections", async () => {
    renderView();

    expect(await screen.findByRole("heading", { name: "Staged extraction review" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Staged Extraction Review" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "LLM Draft Review" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Summary metrics" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Filters" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Batch tools" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Queue items" })).toBeInTheDocument();
  });

  it("does not offer claim filtering in the staged review queue", async () => {
    renderView();

    expect(await screen.findByRole("tab", { name: "Staged Extraction Review" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
  });

  it("shows staged queue stats and extraction items", async () => {
    renderView();

    await waitFor(() => {
      expect(screen.getByText("5")).toBeInTheDocument();
      expect(screen.getByText("82%")).toBeInTheDocument();
      expect(screen.getByText("aspirin")).toBeInTheDocument();
    });
  });

  it("shows empty state when no staged extractions exist", async () => {
    vi.mocked(reviewApi.listPendingExtractions).mockResolvedValue({
      extractions: [],
      total: 0,
      page: 1,
      page_size: 20,
      has_more: false,
    });

    renderView();

    expect(await screen.findByText("review_queue.no_pending_title")).toBeInTheDocument();
  });

  it("enables batch tools only after selection", async () => {
    renderView();
    await screen.findByText("aspirin");

    expect(screen.getByRole("button", { name: "review_queue.approve_selected" })).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));

    await waitFor(() => {
      expect(screen.getByText("review_queue.selected_count")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "review_queue.approve_selected" })).toBeEnabled();
    });
  });

  it("re-fetches when the extraction type filter changes", async () => {
    renderView();
    await screen.findByText("aspirin");

    const initialCallCount = vi.mocked(reviewApi.listPendingExtractions).mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "review_queue.type_entity" }));

    await waitFor(() => {
      expect(vi.mocked(reviewApi.listPendingExtractions).mock.calls.length).toBeGreaterThan(initialCallCount);
    });

    const calls = vi.mocked(reviewApi.listPendingExtractions).mock.calls;
    const lastCallFilters = calls[calls.length - 1][0];
    expect(lastCallFilters?.extraction_type).toBe("entity");
  });

  it("clears selection when a filter change replaces the visible extraction set", async () => {
    vi.mocked(reviewApi.listPendingExtractions)
      .mockResolvedValueOnce({
        extractions: [makeExtraction({ id: "ext-1", extraction_type: "entity" })],
        total: 1,
        page: 1,
        page_size: 20,
        has_more: false,
      })
      .mockResolvedValueOnce({
        extractions: [makeExtraction({ id: "ext-2", extraction_type: "relation" })],
        total: 1,
        page: 1,
        page_size: 20,
        has_more: false,
      });

    renderView();
    await screen.findByText("aspirin");

    fireEvent.click(screen.getByRole("checkbox"));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "review_queue.approve_selected" })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole("button", { name: "review_queue.type_relation" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "review_queue.approve_selected" })).toBeDisabled();
    });
  });

  it("switches to the draft queue with a queue-specific introduction", async () => {
    renderView();
    await screen.findByText("aspirin");

    fireEvent.click(screen.getByRole("tab", { name: "LLM Draft Review" }));

    expect(await screen.findByRole("heading", { name: "LLM draft revision review" })).toBeInTheDocument();
    expect(screen.getByText("Draft panel content")).toBeInTheDocument();
  });
});

/**
 * Tests for ReviewQueueView component.
 *
 * Tests stats display, type/flag filters, selection, batch actions,
 * and the review dialog.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ReviewQueueView } from "../ReviewQueueView";
import { NotificationProvider } from "../../notifications/NotificationContext";
import * as reviewApi from "../../api/extractionReview";

vi.mock("../../api/extractionReview");

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
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => vi.fn() };
});

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
    <NotificationProvider>
      <MemoryRouter>
        <ReviewQueueView />
      </MemoryRouter>
    </NotificationProvider>
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

  it("renders the review queue header", async () => {
    renderView();
    await waitFor(() => {
      expect(screen.getByText("menu.review_queue")).toBeInTheDocument();
    });
  });

  it("displays stats cards after loading", async () => {
    renderView();
    await waitFor(() => {
      expect(screen.getByText("5")).toBeInTheDocument(); // total_pending
      expect(screen.getByText("2")).toBeInTheDocument(); // total_auto_verified
      expect(screen.getByText("1")).toBeInTheDocument(); // flagged_count
    });
  });

  it("displays average score as percentage", async () => {
    renderView();
    await waitFor(() => {
      expect(screen.getByText("82%")).toBeInTheDocument();
    });
  });

  it("renders extraction cards", async () => {
    renderView();
    await waitFor(() => {
      expect(screen.getByText("aspirin")).toBeInTheDocument();
    });
  });

  it("shows empty state when no extractions", async () => {
    vi.mocked(reviewApi.listPendingExtractions).mockResolvedValue({
      extractions: [],
      total: 0,
      page: 1,
      page_size: 20,
      has_more: false,
    });

    renderView();
    await waitFor(() => {
      expect(screen.getByText("review_queue.no_pending_title")).toBeInTheDocument();
    });
  });

  it("shows loading spinner initially", () => {
    vi.mocked(reviewApi.listPendingExtractions).mockImplementation(() => new Promise(() => {}));
    vi.mocked(reviewApi.getReviewStats).mockImplementation(() => new Promise(() => {}));

    renderView();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows batch actions bar when extractions are selected", async () => {
    renderView();
    await waitFor(() => {
      expect(screen.getByText("aspirin")).toBeInTheDocument();
    });

    // Click the checkbox to select
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(screen.getByText(/review_queue.selected_count/)).toBeInTheDocument();
    });
  });

  it("clears selection when deselect all is clicked", async () => {
    renderView();
    await waitFor(() => expect(screen.getByText("aspirin")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("checkbox"));
    await waitFor(() => expect(screen.getByText(/review_queue.selected_count/)).toBeInTheDocument());

    fireEvent.click(screen.getByText("review_queue.deselect_all"));
    await waitFor(() => {
      expect(screen.queryByText(/review_queue.selected_count/)).not.toBeInTheDocument();
    });
  });

  it("opens batch review dialog when Approve Selected is clicked", async () => {
    renderView();
    await waitFor(() => expect(screen.getByText("aspirin")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("checkbox"));
    await waitFor(() => expect(screen.getByText("review_queue.approve_selected")).toBeInTheDocument());

    fireEvent.click(screen.getByText("review_queue.approve_selected"));
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("selects all extractions when Select All is clicked", async () => {
    renderView();
    await waitFor(() => expect(screen.getByText("aspirin")).toBeInTheDocument());

    fireEvent.click(screen.getByText("review_queue.select_all"));
    await waitFor(() => {
      expect(screen.getByText(/review_queue.selected_count/)).toBeInTheDocument();
    });
  });

  it("type filter toggles trigger re-fetch with extraction_type filter", async () => {
    renderView();
    await waitFor(() => expect(screen.getByText("aspirin")).toBeInTheDocument());

    const initialCallCount = vi.mocked(reviewApi.listPendingExtractions).mock.calls.length;

    const entityButton = screen.getByText("review_queue.type_entity");
    fireEvent.click(entityButton);

    // After clicking Entity filter, the API should be called again
    await waitFor(() => {
      const newCallCount = vi.mocked(reviewApi.listPendingExtractions).mock.calls.length;
      expect(newCallCount).toBeGreaterThan(initialCallCount);
    });

    // The latest call should include extraction_type=entity
    const calls = vi.mocked(reviewApi.listPendingExtractions).mock.calls;
    const lastCallFilters = calls[calls.length - 1][0];
    expect(lastCallFilters?.extraction_type).toBe("entity");
  });

  it("shows load more button when has_more is true", async () => {
    vi.mocked(reviewApi.listPendingExtractions).mockResolvedValue({
      extractions: [makeExtraction()],
      total: 5,
      page: 1,
      page_size: 20,
      has_more: true,
    });

    renderView();
    await waitFor(() => {
      expect(screen.getByText("common.load_more")).toBeInTheDocument();
    });
  });
});

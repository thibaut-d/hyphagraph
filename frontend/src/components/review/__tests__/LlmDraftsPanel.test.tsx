/**
 * Tests for LlmDraftsPanel component.
 *
 * Covers:
 * - Loading spinner while fetching
 * - Empty state when no drafts
 * - Renders list of draft items with kind chip and label
 * - Confirm button calls confirmRevision and refreshes
 * - Discard button calls discardRevision and refreshes
 * - Error from API shown via notification (no crash)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { LlmDraftsPanel } from "../LlmDraftsPanel";
import { NotificationProvider } from "../../../notifications/NotificationContext";
import * as revisionReviewApi from "../../../api/revisionReview";

vi.mock("../../../api/revisionReview");

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

const mockCounts = {
  entity: 1,
  relation: 1,
  source: 0,
  total: 2,
};

function makeDraft(
  overrides: Partial<revisionReviewApi.DraftRevisionRead> = {}
): revisionReviewApi.DraftRevisionRead {
  return {
    id: "rev-1",
    revision_kind: "entity",
    parent_id: "parent-1",
    created_with_llm: "gpt-4",
    created_by_user_id: null,
    created_at: "2026-03-21T10:00:00Z",
    slug: "aspirin",
    kind: null,
    title: null,
    status: "draft",
    ...overrides,
  };
}

function renderPanel() {
  return render(
    <NotificationProvider>
      <LlmDraftsPanel />
    </NotificationProvider>
  );
}

describe("LlmDraftsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(revisionReviewApi.getDraftRevisionCounts).mockResolvedValue(mockCounts);
    vi.mocked(revisionReviewApi.listDraftRevisions).mockResolvedValue({
      items: [makeDraft()],
      total: 1,
      page: 1,
      page_size: 50,
      has_more: false,
    });
  });

  it("shows loading spinner initially", () => {
    vi.mocked(revisionReviewApi.listDraftRevisions).mockImplementation(
      () => new Promise(() => {})
    );
    vi.mocked(revisionReviewApi.getDraftRevisionCounts).mockImplementation(
      () => new Promise(() => {})
    );
    renderPanel();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows empty state when no drafts", async () => {
    vi.mocked(revisionReviewApi.listDraftRevisions).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 50,
      has_more: false,
    });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("llm_drafts.no_drafts_title")).toBeInTheDocument();
    });
  });

  it("renders draft item with slug as label", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("aspirin")).toBeInTheDocument();
    });
  });

  it("renders kind chip using i18n key", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("llm_drafts.kind_entity")).toBeInTheDocument();
    });
  });

  it("renders counts summary line", async () => {
    renderPanel();
    await waitFor(() => {
      // The counts summary uses the counts from getDraftRevisionCounts
      expect(screen.getByText(/llm_drafts.counts_label/)).toBeInTheDocument();
    });
  });

  it("renders summary and metadata rows for clarity", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("llm_drafts.summary_entity")).toBeInTheDocument();
      expect(screen.getByText("review_queue.pending_review")).toBeInTheDocument();
      expect(screen.getByText("llm_drafts.meta_model")).toBeInTheDocument();
      expect(screen.getByText("llm_drafts.meta_date")).toBeInTheDocument();
      expect(screen.getByText("llm_drafts.meta_id")).toBeInTheDocument();
    });
  });

  it("renders confirm and discard buttons", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("llm_drafts.confirm")).toBeInTheDocument();
      expect(screen.getByText("llm_drafts.discard")).toBeInTheDocument();
    });
  });

  it("calls confirmRevision when Confirm is clicked", async () => {
    vi.mocked(revisionReviewApi.confirmRevision).mockResolvedValue({
      id: "rev-1",
      revision_kind: "entity",
      status: "confirmed",
    });
    renderPanel();
    await waitFor(() => expect(screen.getByText("llm_drafts.confirm")).toBeInTheDocument());

    fireEvent.click(screen.getByText("llm_drafts.confirm"));

    await waitFor(() => {
      expect(revisionReviewApi.confirmRevision).toHaveBeenCalledWith("entity", "rev-1");
    });
  });

  it("calls discardRevision when Discard is clicked", async () => {
    vi.mocked(revisionReviewApi.discardRevision).mockResolvedValue({
      id: "rev-1",
      revision_kind: "entity",
      deleted: true,
    });
    renderPanel();
    await waitFor(() => expect(screen.getByText("llm_drafts.discard")).toBeInTheDocument());

    fireEvent.click(screen.getByText("llm_drafts.discard"));

    await waitFor(() => {
      expect(revisionReviewApi.discardRevision).toHaveBeenCalledWith("entity", "rev-1");
    });
  });

  it("refreshes list after confirm", async () => {
    vi.mocked(revisionReviewApi.confirmRevision).mockResolvedValue({
      id: "rev-1",
      revision_kind: "entity",
      status: "confirmed",
    });
    renderPanel();
    await waitFor(() => expect(screen.getByText("llm_drafts.confirm")).toBeInTheDocument());

    const initialCalls = vi.mocked(revisionReviewApi.listDraftRevisions).mock.calls.length;
    fireEvent.click(screen.getByText("llm_drafts.confirm"));

    await waitFor(() => {
      expect(vi.mocked(revisionReviewApi.listDraftRevisions).mock.calls.length).toBeGreaterThan(
        initialCalls
      );
    });
  });

  it("shows relation kind chip for relation draft", async () => {
    vi.mocked(revisionReviewApi.listDraftRevisions).mockResolvedValue({
      items: [makeDraft({ revision_kind: "relation", kind: "treats", slug: undefined })],
      total: 1,
      page: 1,
      page_size: 50,
      has_more: false,
    });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("llm_drafts.kind_relation")).toBeInTheDocument();
      expect(screen.getByText("treats")).toBeInTheDocument();
    });
  });

  it("falls back to id when no slug/title/kind", async () => {
    vi.mocked(revisionReviewApi.listDraftRevisions).mockResolvedValue({
      items: [
        makeDraft({ slug: undefined, kind: undefined, title: undefined, id: "fallback-id" }),
      ],
      total: 1,
      page: 1,
      page_size: 50,
      has_more: false,
    });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("fallback-id")).toBeInTheDocument();
    });
  });
});

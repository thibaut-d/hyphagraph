import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  listAllExtractions,
  listPendingExtractions,
} from "../extractionReview";

vi.mock("../client", () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from "../client";

describe("Extraction review API client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiFetch).mockResolvedValue({
      extractions: [],
      total: 0,
      page: 1,
      page_size: 20,
      has_more: false,
    });
  });

  it("serializes all supported pending filters", async () => {
    await listPendingExtractions({
      extraction_type: "relation",
      source_id: "source-1",
      min_validation_score: 0.25,
      max_validation_score: 0.9,
      has_flags: true,
      auto_commit_eligible: false,
      page: 2,
      page_size: 50,
      sort_by: "validation_score",
      sort_order: "desc",
    });

    expect(apiFetch).toHaveBeenCalledWith(
      "/extraction-review/pending?extraction_type=relation&source_id=source-1&min_validation_score=0.25&max_validation_score=0.9&has_flags=true&auto_commit_eligible=false&page=2&page_size=50&sort_by=validation_score&sort_order=desc"
    );
  });

  it("serializes all supported admin filters", async () => {
    await listAllExtractions({
      status: "pending",
      extraction_type: "relation",
      source_id: "source-2",
      min_validation_score: 0.4,
      max_validation_score: 0.8,
      has_flags: false,
      auto_commit_eligible: true,
      page: 3,
      page_size: 25,
      sort_by: "created_at",
      sort_order: "asc",
    });

    expect(apiFetch).toHaveBeenCalledWith(
      "/extraction-review/all?status=pending&extraction_type=relation&source_id=source-2&min_validation_score=0.4&max_validation_score=0.8&has_flags=false&auto_commit_eligible=true&page=3&page_size=25&sort_by=created_at&sort_order=asc"
    );
  });
});

/**
 * API client for extraction review endpoints.
 *
 * Handles human-in-the-loop review of LLM extractions.
 */
import { apiFetch } from "./client";

export interface StagedExtractionRead {
  id: string;
  extraction_type: "entity" | "relation" | "claim";
  status: "auto_verified" | "pending" | "approved" | "rejected";
  source_id: string;
  extraction_data: any; // JSON - original LLM output
  validation_score: number;
  validation_flags: string[];
  materialized_entity_id?: string;
  materialized_relation_id?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
  llm_model?: string;
  llm_provider?: string;
  created_at: string;
}

export interface StagedExtractionListResponse {
  extractions: StagedExtractionRead[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface ReviewStats {
  total_pending: number;
  total_approved: number;
  total_rejected: number;
  total_auto_verified: number;
  pending_entities: number;
  pending_relations: number;
  pending_claims: number;
  avg_validation_score: number;
  flagged_count: number;
}

export interface ReviewDecisionRequest {
  decision: "approve" | "reject";
  notes?: string;
}

export interface BatchReviewRequest {
  extraction_ids: string[];
  decision: "approve" | "reject";
  notes?: string;
}

export interface BatchReviewResponse {
  succeeded: number;
  failed: number;
}

export interface StagedExtractionFilters {
  status?: "auto_verified" | "pending" | "approved" | "rejected";
  extraction_type?: "entity" | "relation" | "claim";
  source_id?: string;
  min_validation_score?: number;
  max_validation_score?: number;
  has_flags?: boolean;
  page?: number;
  page_size?: number;
}

/**
 * List pending extractions that need review.
 *
 * GET /api/extraction-review/pending
 */
export async function listPendingExtractions(
  filters?: StagedExtractionFilters
): Promise<StagedExtractionListResponse> {
  const params = new URLSearchParams();

  if (filters?.min_validation_score !== undefined) {
    params.append("min_validation_score", filters.min_validation_score.toString());
  }
  if (filters?.max_validation_score !== undefined) {
    params.append("max_validation_score", filters.max_validation_score.toString());
  }
  if (filters?.has_flags !== undefined) {
    params.append("has_flags", filters.has_flags.toString());
  }
  if (filters?.page) {
    params.append("page", filters.page.toString());
  }
  if (filters?.page_size) {
    params.append("page_size", filters.page_size.toString());
  }

  const queryString = params.toString();
  const url = queryString
    ? `/extraction-review/pending?${queryString}`
    : "/extraction-review/pending";

  return apiFetch<StagedExtractionListResponse>(url);
}

/**
 * Get review statistics.
 *
 * GET /api/extraction-review/stats
 */
export async function getReviewStats(): Promise<ReviewStats> {
  return apiFetch<ReviewStats>("/extraction-review/stats");
}

/**
 * Get a single staged extraction by ID.
 *
 * GET /api/extraction-review/{id}
 */
export async function getStagedExtraction(
  extractionId: string
): Promise<StagedExtractionRead> {
  return apiFetch<StagedExtractionRead>(`/extraction-review/${extractionId}`);
}

/**
 * Review an extraction (approve or reject).
 *
 * POST /api/extraction-review/{id}/review
 */
export async function reviewExtraction(
  extractionId: string,
  request: ReviewDecisionRequest
): Promise<{ success: boolean; message?: string }> {
  return apiFetch<{ success: boolean; message?: string }>(
    `/extraction-review/${extractionId}/review`,
    {
      method: "POST",
      body: JSON.stringify(request),
    }
  );
}

/**
 * Batch review multiple extractions.
 *
 * POST /api/extraction-review/batch-review
 */
export async function batchReview(
  request: BatchReviewRequest
): Promise<BatchReviewResponse> {
  return apiFetch<BatchReviewResponse>("/extraction-review/batch-review", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

/**
 * List all extractions with filtering (admin only).
 *
 * GET /api/extraction-review/all
 */
export async function listAllExtractions(
  filters?: StagedExtractionFilters
): Promise<StagedExtractionListResponse> {
  const params = new URLSearchParams();

  if (filters?.status) {
    params.append("status", filters.status);
  }
  if (filters?.extraction_type) {
    params.append("extraction_type", filters.extraction_type);
  }
  if (filters?.source_id) {
    params.append("source_id", filters.source_id);
  }
  if (filters?.page) {
    params.append("page", filters.page.toString());
  }
  if (filters?.page_size) {
    params.append("page_size", filters.page_size.toString());
  }

  const queryString = params.toString();
  const url = queryString
    ? `/extraction-review/all?${queryString}`
    : "/extraction-review/all";

  return apiFetch<StagedExtractionListResponse>(url);
}

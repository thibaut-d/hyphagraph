/**
 * API client for extraction review endpoints.
 *
 * Handles human-in-the-loop review of LLM extractions.
 */
import { apiFetch } from "./client";
import type {
  ExtractedClaim,
  ExtractedEntity,
  ExtractedRelation,
} from "../types/extraction";

export type ReviewDecision = "approve" | "reject";
export type ExtractionStatus = "auto_verified" | "pending" | "approved" | "rejected";
export type ExtractionType = "entity" | "relation" | "claim";
export type StagedExtractionData = ExtractedEntity | ExtractedRelation | ExtractedClaim;

export interface StagedExtractionRead {
  id: string;
  extraction_type: ExtractionType;
  status: ExtractionStatus;
  source_id: string;
  extraction_data: StagedExtractionData;
  validation_score: number;
  confidence_adjustment: number;
  validation_flags: string[];
  matched_span?: string | null;
  materialized_entity_id?: string;
  materialized_relation_id?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
  llm_model?: string;
  llm_provider?: string;
  auto_commit_eligible: boolean;
  auto_commit_threshold?: number | null;
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
  high_confidence_count: number;
  flagged_count: number;
}

export interface ReviewDecisionRequest {
  decision: ReviewDecision;
  notes?: string;
}

export interface BatchReviewRequest {
  extraction_ids: string[];
  decision: ReviewDecision;
  notes?: string;
}

export interface BatchReviewResponse {
  total_requested: number;
  succeeded: number;
  failed: number;
  failed_ids: string[];
  materialized_entities: string[];
  materialized_relations: string[];
}

export interface MaterializationResult {
  success: boolean;
  extraction_id: string;
  extraction_type: ExtractionType;
  materialized_entity_id?: string | null;
  materialized_relation_id?: string | null;
  error?: string | null;
}

export interface StagedExtractionFilters {
  status?: ExtractionStatus;
  extraction_type?: ExtractionType;
  source_id?: string;
  min_validation_score?: number;
  max_validation_score?: number;
  has_flags?: boolean;
  auto_commit_eligible?: boolean;
  page?: number;
  page_size?: number;
  sort_by?: "created_at" | "validation_score" | "confidence_adjustment";
  sort_order?: "asc" | "desc";
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
  if (filters?.sort_by) {
    params.append("sort_by", filters.sort_by);
  }
  if (filters?.sort_order) {
    params.append("sort_order", filters.sort_order);
  }
  if (filters?.auto_commit_eligible !== undefined) {
    params.append("auto_commit_eligible", filters.auto_commit_eligible.toString());
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
): Promise<MaterializationResult> {
  return apiFetch<MaterializationResult>(
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

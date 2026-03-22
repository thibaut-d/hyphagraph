/**
 * API client for explainability endpoints.
 *
 * Provides functions to fetch detailed explanations of computed inferences,
 * including source chains, confidence breakdowns, and contradiction analysis.
 */

import { apiFetch } from "./client";
import { ScopeFilter } from "./inferences";
import { appendOptionalJson, buildQueryString, createSearchParams } from "./queryString";


export interface SourceContribution {
  source_id: string;
  source_title: string;
  source_authors?: string[];
  source_year?: number;
  source_kind: string;
  source_trust?: number | null;
  source_url: string;

  relation_id: string;
  relation_kind: string;
  relation_direction: string;
  relation_confidence: number;
  relation_scope?: ScopeFilter | null;

  role_weight?: number | null;
  contribution_percentage: number;
}


export interface ContradictionDetail {
  supporting_sources: SourceContribution[];
  contradicting_sources: SourceContribution[];
  disagreement_score: number;
}


export interface ConfidenceFactor {
  factor: string;
  value: number;
  explanation: string;
}


export interface SummaryData {
  source_count: number;
  score: number | null;
  direction: "strong_positive" | "weak_positive" | "neutral" | "weak_negative" | "strong_negative" | "none";
  confidence_level: "high" | "moderate" | "low";
  confidence_pct: number;
  disagreement_level: "significant" | "some" | "none";
  role_type: string;
}

/** Compose localised prose from a SummaryData value. */
export function formatExplanationSummary(
  summary: SummaryData,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string {
  const direction = t(`explanation.summary_direction_${summary.direction}`);
  const confidenceLevel = t(`explanation.summary_confidence_${summary.confidence_level}`);
  const intro = t("explanation.summary_intro", {
    count: summary.source_count,
    role: summary.role_type,
    direction,
    confidence_level: confidenceLevel,
    pct: summary.confidence_pct,
  });
  const disagreement = t(`explanation.summary_disagreement_${summary.disagreement_level}`);
  return `${intro} ${disagreement}`;
}


export interface ExplanationRead {
  entity_id: string;
  role_type: string;
  score: number | null;
  confidence: number;
  disagreement: number;

  summary: SummaryData;
  confidence_factors: ConfidenceFactor[];
  contradictions?: ContradictionDetail;
  source_chain: SourceContribution[];
  scope_filter?: ScopeFilter | null;
}


/**
 * Fetch detailed explanation for a computed inference.
 *
 * @param entityId - Entity to explain inference for
 * @param roleType - Role to explain (e.g., "drug", "condition", "effect")
 * @param scopeFilter - Optional scope filter (same format as inference API)
 * @returns Detailed explanation with source chain, confidence breakdown, and contradictions
 */
export function getExplanation(
  entityId: string,
  roleType: string,
  scopeFilter?: ScopeFilter
): Promise<ExplanationRead> {
  const params = createSearchParams((query) => {
    appendOptionalJson(query, "scope", scopeFilter);
  });
  return apiFetch(`/explain/inference/${entityId}/${roleType}${buildQueryString(params)}`);
}

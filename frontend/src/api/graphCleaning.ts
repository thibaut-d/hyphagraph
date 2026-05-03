import { apiFetch } from "./client";

export interface CleaningRelationRole {
  entity_id: string;
  entity_slug: string | null;
  role_type: string;
}

export interface DuplicateRelationItem {
  relation_id: string;
  source_title: string | null;
  kind: string | null;
  direction: string | null;
  confidence: number | null;
  roles: CleaningRelationRole[];
}

export interface DuplicateRelationCandidate {
  fingerprint: string;
  reason: string;
  relation_count: number;
  source_title: string | null;
  relations: DuplicateRelationItem[];
}

export interface RoleUsageCount {
  role_type: string;
  count: number;
  relation_ids: string[];
}

export interface RoleConsistencyCandidate {
  entity_id: string;
  entity_slug: string | null;
  relation_kind: string | null;
  reason: string;
  usages: RoleUsageCount[];
}

export interface GraphCleaningAnalysis {
  duplicate_relations: DuplicateRelationCandidate[];
  role_consistency: RoleConsistencyCandidate[];
}

export interface GraphCleaningDecision {
  id: string;
  candidate_type: "entity_merge" | "duplicate_relation" | "role_consistency";
  candidate_fingerprint: string;
  status: "open" | "dismissed" | "approved" | "applied" | "needs_review";
  notes: string | null;
  decision_payload: Record<string, unknown> | null;
  action_result: Record<string, unknown> | null;
  reviewed_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface GraphCleaningCritiqueItem {
  candidate_fingerprint: string;
  recommendation: "recommend" | "reject" | "needs_human_review";
  rationale: string;
  risks: string[];
  evidence_gaps: string[];
}

export interface GraphCleaningCritiqueResponse {
  model: string;
  items: GraphCleaningCritiqueItem[];
}

export function getGraphCleaningAnalysis(limit = 50): Promise<GraphCleaningAnalysis> {
  return apiFetch(`/admin/graph-cleaning/analysis?limit=${limit}`);
}

export function listGraphCleaningDecisions(): Promise<GraphCleaningDecision[]> {
  return apiFetch("/admin/graph-cleaning/decisions");
}

export function saveGraphCleaningDecision(
  payload: Pick<
    GraphCleaningDecision,
    "candidate_type" | "candidate_fingerprint" | "status" | "notes" | "decision_payload"
  >,
): Promise<GraphCleaningDecision> {
  return apiFetch("/admin/graph-cleaning/decisions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function critiqueGraphCleaningCandidates(
  candidates: Record<string, unknown>[],
): Promise<GraphCleaningCritiqueResponse> {
  return apiFetch("/admin/graph-cleaning/critique", {
    method: "POST",
    body: JSON.stringify({ candidates }),
  });
}

export function applyDuplicateRelationReview(payload: {
  duplicate_relation_ids: string[];
  rationale: string;
  candidate_fingerprint?: string;
}) {
  return apiFetch("/admin/graph-cleaning/duplicate-relations/apply", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function applyRoleCorrection(
  relationId: string,
  payload: {
    corrections: Array<{
      entity_id: string;
      from_role_type: string;
      to_role_type: string;
    }>;
    rationale: string;
    candidate_fingerprint?: string;
  },
) {
  return apiFetch(`/admin/graph-cleaning/relations/${relationId}/correct-roles`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

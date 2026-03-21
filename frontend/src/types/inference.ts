import { RelationRead } from "./relation";
import { SourceRead } from "./source";

export interface EntityRoleInference {
  entity_slug: string;  // The linked entity
  semantic_role: string;  // Semantic role of this entity (agent, target, population, etc.)
  score: number | null;  // Normalized inference score in [-1, 1]
  coverage: number;  // Information coverage (number of relations with this entity+role)
  confidence: number;  // Confidence in [0, 1)
  disagreement: number;  // Contradiction measure in [0, 1]
}

export interface RoleInference {
  role_type: string;  // Semantic role (agent, target, drug, condition, etc.)
  score: number | null;  // Aggregated score in [-1, 1]
  coverage: number;  // Information coverage (number of relations)
  confidence: number;  // Confidence in [0, 1)
  disagreement: number;  // Contradiction measure in [0, 1]
}

export interface InferenceRead {
  entity_id: string;
  relations_by_kind: Record<string, RelationRead[]>;
  role_inferences?: RoleInference[];
}

export interface EvidenceItemRead extends RelationRead {
  source?: SourceRead | null;
}

export interface RelationKindSummaryRead {
  kind: string;
  relation_count: number;
  average_confidence: number;
  supporting_count: number;
  contradicting_count: number;
  neutral_count: number;
}

export interface DisagreementGroupRead {
  kind: string;
  supporting: EvidenceItemRead[];
  contradicting: EvidenceItemRead[];
  confidence: number;
}

export interface InferenceStatsRead {
  total_relations: number;
  unique_sources_count: number;
  average_confidence: number;
  confidence_count: number;
  high_confidence_count: number;
  low_confidence_count: number;
  contradiction_count: number;
  relation_type_count: number;
}

export interface InferenceDetailRead extends InferenceRead {
  stats: InferenceStatsRead;
  relation_kind_summaries: RelationKindSummaryRead[];
  evidence_items: EvidenceItemRead[];
  disagreement_groups: DisagreementGroupRead[];
}

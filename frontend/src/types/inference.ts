import { RelationRead } from "./relation";

export interface EntityRoleInference {
  entity_slug: string;  // The linked entity
  semantic_role: string;  // Semantic role of this entity (agent, target, population, etc.)
  score: number | null;  // Normalized inference score in [-1, 1]
  coverage: number;  // Information coverage (number of relations with this entity+role)
  confidence: number;  // Confidence in [0, 1)
  disagreement: number;  // Contradiction measure in [0, 1]
  source_count: number;  // Number of sources supporting this
}

export interface RoleInference {
  relation_type: string;  // Type of relation (treats, biomarker_for, etc.)
  semantic_role: string;  // Semantic role being analyzed (agent, target, etc.)
  entity_inferences: EntityRoleInference[];  // Per-entity scores
  // Aggregated metrics (for overview)
  total_entities: number;
  avg_score: number | null;
  avg_confidence: number;
}

export interface InferenceRead {
  entity_id: string;
  relations_by_kind: Record<string, RelationRead[]>;
  role_inferences: RoleInference[];
}
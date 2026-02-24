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
  role_type: string;  // Semantic role (agent, target, drug, condition, etc.)
  score: number | null;  // Aggregated score in [-1, 1]
  coverage: number;  // Information coverage (number of relations)
  confidence: number;  // Confidence in [0, 1)
  disagreement: number;  // Contradiction measure in [0, 1]
}

export interface InferenceRead {
  entity_id: string;
  relations_by_kind: Record<string, RelationRead[]>;
  role_inferences: RoleInference[];
}
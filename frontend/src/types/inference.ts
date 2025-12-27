import { RelationRead } from "./relation";

export interface RoleInference {
  role_type: string;
  score: number | null;  // Normalized inference score in [-1, 1]
  coverage: number;  // Information coverage
  confidence: number;  // Confidence in [0, 1)
  disagreement: number;  // Contradiction measure in [0, 1]
}

export interface InferenceRead {
  entity_id: string;
  relations_by_kind: Record<string, RelationRead[]>;
  role_inferences: RoleInference[];
}
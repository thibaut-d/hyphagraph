import { RelationRead } from "./relation";

export interface InferenceRead {
  entity_id: string;
  relations_by_kind: Record<string, RelationRead[]>;
}
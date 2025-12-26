import { apiFetch } from "./client";
import { RelationRead } from "../types/relation";

export function listRelationsBySource(sourceId: string): Promise<RelationRead[]> {
  return apiFetch(`/relations/by-source/${sourceId}`);
}
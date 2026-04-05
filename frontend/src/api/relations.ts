import { apiFetch } from "./client";
import type { RelationRead } from "../types/relation";
import type { JsonObject } from "../types/json";

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface RoleWrite {
  entity_id: string;
  role_type: string;
  weight?: number;
  coverage?: number;
}

export interface RelationWrite {
  source_id: string;
  kind: string;
  direction?: string;
  confidence?: number;
  scope?: JsonObject | null;
  notes?: Record<string, string>;
  roles: RoleWrite[];
  created_with_llm?: string;
}

export function listRelationsBySource(sourceId: string): Promise<RelationRead[]> {
  return apiFetch(`/relations/by-source/${sourceId}`);
}

export function listRelations(limit = 50, offset = 0): Promise<PaginatedResponse<RelationRead>> {
  return apiFetch(`/relations?limit=${limit}&offset=${offset}`);
}

export function getRelation(relationId: string): Promise<RelationRead> {
  return apiFetch(`/relations/${relationId}`);
}

export function createRelation(payload: RelationWrite): Promise<RelationRead> {
  return apiFetch("/relations/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateRelation(id: string, payload: RelationWrite): Promise<RelationRead> {
  return apiFetch(`/relations/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteRelation(id: string): Promise<void> {
  return apiFetch(`/relations/${id}`, {
    method: "DELETE",
  });
}

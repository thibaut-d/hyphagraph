import { apiFetch } from "./client";
import { RelationRead } from "../types/relation";

export interface RoleWrite {
  entity_id: string;
  role_type: string;
  weight?: number;
  coverage?: number;
}

export interface RelationWrite {
  source_id: string;
  kind?: string;
  direction?: string;
  confidence?: number;
  scope?: Record<string, any>;
  notes?: Record<string, string>;
  roles: RoleWrite[];
  created_with_llm?: string;
}

export function listRelationsBySource(sourceId: string): Promise<RelationRead[]> {
  return apiFetch(`/relations/by-source/${sourceId}`);
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
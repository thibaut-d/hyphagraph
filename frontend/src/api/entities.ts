import { apiFetch } from "./client";
import { EntityRead } from "../types/entity";

export interface EntityWrite {
  slug: string;
  summary?: Record<string, string>;
  ui_category_id?: string;
  created_with_llm?: string;
  kind?: string;
  label?: string;
  synonyms?: string[];
  ontology_ref?: string;
}

export function listEntities(): Promise<EntityRead[]> {
  return apiFetch("/entities");
}

export function getEntity(id: string): Promise<EntityRead> {
  return apiFetch(`/entities/${id}`);
}

export function createEntity(payload: EntityWrite): Promise<EntityRead> {
  return apiFetch("/entities/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateEntity(id: string, payload: EntityWrite): Promise<EntityRead> {
  return apiFetch(`/entities/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteEntity(id: string): Promise<void> {
  return apiFetch(`/entities/${id}`, {
    method: "DELETE",
  });
}
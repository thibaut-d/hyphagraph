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

export interface EntityFilters {
  ui_category_id?: string[];
  search?: string;
}

export function listEntities(filters?: EntityFilters): Promise<EntityRead[]> {
  const params = new URLSearchParams();

  if (filters?.ui_category_id) {
    filters.ui_category_id.forEach(id => params.append('ui_category_id', id));
  }

  if (filters?.search) {
    params.append('search', filters.search);
  }

  const queryString = params.toString();
  return apiFetch(`/entities${queryString ? `?${queryString}` : ''}`);
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
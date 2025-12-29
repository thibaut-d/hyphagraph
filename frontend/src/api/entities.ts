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
  limit?: number;
  offset?: number;
}

export interface UICategoryOption {
  id: string;
  label: Record<string, string>; // i18n: { en: "Drug", fr: "Médicament" }
}

export interface EntityFilterOptions {
  ui_categories: UICategoryOption[];
  consensus_levels: [number, number] | null;
  evidence_quality_range: [number, number] | null;
  year_range: [number, number] | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export function listEntities(filters?: EntityFilters): Promise<PaginatedResponse<EntityRead>> {
  const params = new URLSearchParams();

  if (filters?.ui_category_id) {
    filters.ui_category_id.forEach(id => params.append('ui_category_id', id));
  }

  if (filters?.search) {
    params.append('search', filters.search);
  }

  if (filters?.limit !== undefined) {
    params.append('limit', filters.limit.toString());
  }

  if (filters?.offset !== undefined) {
    params.append('offset', filters.offset.toString());
  }

  const queryString = params.toString();
  return apiFetch(`/entities${queryString ? `?${queryString}` : ''}`);
}

export function getEntity(id: string): Promise<EntityRead> {
  return apiFetch(`/entities/${id}`);
}

export function createEntity(payload: EntityWrite): Promise<EntityRead> {
  return apiFetch("/entities", {
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

export function getEntityFilterOptions(): Promise<EntityFilterOptions> {
  return apiFetch("/entities/filter-options");
}

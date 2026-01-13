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
  clinical_effects?: string[];
  consensus_level?: string[];
  evidence_quality_min?: number;
  evidence_quality_max?: number;
  recency?: string[];
  limit?: number;
  offset?: number;
}

export interface UICategoryOption {
  id: string;
  label: Record<string, string>; // i18n: { en: "Drug", fr: "Médicament" }
}

export interface ClinicalEffectOption {
  type_id: string;
  label: Record<string, string>;
}

export interface EntityFilterOptions {
  ui_categories: UICategoryOption[];
  clinical_effects?: ClinicalEffectOption[];
  consensus_levels?: string[];
  evidence_quality_range?: [number, number];
  recency_options?: string[];
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

  if (filters?.clinical_effects) {
    filters.clinical_effects.forEach(effect => params.append('clinical_effects', effect));
  }

  if (filters?.consensus_level) {
    filters.consensus_level.forEach(level => params.append('consensus_level', level));
  }

  if (filters?.evidence_quality_min !== undefined) {
    params.append('evidence_quality_min', filters.evidence_quality_min.toString());
  }

  if (filters?.evidence_quality_max !== undefined) {
    params.append('evidence_quality_max', filters.evidence_quality_max.toString());
  }

  if (filters?.recency) {
    filters.recency.forEach(r => params.append('recency', r));
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

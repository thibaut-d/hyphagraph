import { apiFetch } from "./client";
import {
  appendArrayParam,
  appendOptionalNumber,
  appendOptionalParam,
  buildQueryString,
  createSearchParams,
} from "./queryString";
import type { EntityRead } from "../types/entity";
export type { EntityRead } from "../types/entity";

export interface EntityWrite {
  slug: string;
  summary?: Record<string, string>;
  ui_category_id?: string;
  created_with_llm?: string;
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
  clinical_effects?: ClinicalEffectOption[] | null;
  consensus_levels?: string[] | null;
  evidence_quality_range?: [number, number] | null;
  year_range?: [number, number] | null;
  recency_options?: string[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export function listEntities(filters?: EntityFilters): Promise<PaginatedResponse<EntityRead>> {
  const params = createSearchParams((query) => {
    appendArrayParam(query, "ui_category_id", filters?.ui_category_id);
    appendOptionalParam(query, "search", filters?.search);
    appendArrayParam(query, "clinical_effects", filters?.clinical_effects);
    appendArrayParam(query, "consensus_level", filters?.consensus_level);
    appendOptionalNumber(query, "evidence_quality_min", filters?.evidence_quality_min);
    appendOptionalNumber(query, "evidence_quality_max", filters?.evidence_quality_max);
    appendArrayParam(query, "recency", filters?.recency);
    appendOptionalNumber(query, "limit", filters?.limit);
    appendOptionalNumber(query, "offset", filters?.offset);
  });

  return apiFetch(`/entities${buildQueryString(params)}`);
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

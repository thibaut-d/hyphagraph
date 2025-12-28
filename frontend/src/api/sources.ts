import { apiFetch } from "./client";
import { SourceRead } from "../types/source";

export interface SourceWrite {
  kind: string;
  title: string;
  authors?: string[];
  year?: number;
  origin?: string;
  url: string;
  trust_level?: number;
  summary?: Record<string, string>;
  source_metadata?: Record<string, any>;
  created_with_llm?: string;
}

export interface SourceFilters {
  kind?: string[];
  year_min?: number;
  year_max?: number;
  trust_level_min?: number;
  trust_level_max?: number;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface SourceFilterOptions {
  kinds: string[];
  year_range: [number, number] | null;
}

export function listSources(filters?: SourceFilters): Promise<PaginatedResponse<SourceRead>> {
  const params = new URLSearchParams();

  if (filters?.kind) {
    filters.kind.forEach(k => params.append('kind', k));
  }

  if (filters?.year_min !== undefined) {
    params.append('year_min', filters.year_min.toString());
  }

  if (filters?.year_max !== undefined) {
    params.append('year_max', filters.year_max.toString());
  }

  if (filters?.trust_level_min !== undefined) {
    params.append('trust_level_min', filters.trust_level_min.toString());
  }

  if (filters?.trust_level_max !== undefined) {
    params.append('trust_level_max', filters.trust_level_max.toString());
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
  return apiFetch(`/sources${queryString ? `?${queryString}` : ''}`);
}

export function getSource(id: string): Promise<SourceRead> {
  return apiFetch(`/sources/${id}`);
}

export function createSource(payload: SourceWrite): Promise<SourceRead> {
  return apiFetch("/sources/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSource(id: string, payload: SourceWrite): Promise<SourceRead> {
  return apiFetch(`/sources/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteSource(id: string): Promise<void> {
  return apiFetch(`/sources/${id}`, {
    method: "DELETE",
  });
}

export function getSourceFilterOptions(): Promise<SourceFilterOptions> {
  return apiFetch("/sources/filter-options");
}
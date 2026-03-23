import { apiFetch } from "./client";
import {
  appendArrayParam,
  appendOptionalNumber,
  appendOptionalParam,
  buildQueryString,
  createSearchParams,
} from "./queryString";
import type { SourceRead, SourceWrite } from "../types/source";
import type { JsonObject } from "../types/json";

export type { SourceWrite } from "../types/source";

export interface SourceFilters {
  kind?: string[];
  year_min?: number;
  year_max?: number;
  trust_level_min?: number;
  trust_level_max?: number;
  search?: string;
  domain?: string[];
  role?: string[];
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset?: number;
}

export interface SourceFilterOptions {
  kinds: string[];
  year_range: [number, number] | null;
  domains?: string[];
  roles?: string[];
}

export interface SourceMetadataSuggestion {
  url: string;
  title?: string | null;
  authors?: string[] | null;
  year?: number | null;
  origin?: string | null;
  kind?: string | null;
  trust_level?: number | null;
  summary?: Record<string, string> | null;
  source_metadata?: JsonObject | null;
}

export function extractMetadataFromUrl(url: string): Promise<SourceMetadataSuggestion> {
  return apiFetch("/sources/extract-metadata-from-url", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function listSources(filters?: SourceFilters): Promise<PaginatedResponse<SourceRead>> {
  const params = createSearchParams((query) => {
    appendArrayParam(query, "kind", filters?.kind);
    appendOptionalNumber(query, "year_min", filters?.year_min);
    appendOptionalNumber(query, "year_max", filters?.year_max);
    appendOptionalNumber(query, "trust_level_min", filters?.trust_level_min);
    appendOptionalNumber(query, "trust_level_max", filters?.trust_level_max);
    appendOptionalParam(query, "search", filters?.search);
    appendArrayParam(query, "domain", filters?.domain);
    appendArrayParam(query, "role", filters?.role);
    appendOptionalNumber(query, "limit", filters?.limit);
    appendOptionalNumber(query, "offset", filters?.offset);
  });

  return apiFetch(`/sources${buildQueryString(params)}`);
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

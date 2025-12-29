import { apiFetch } from "./client";

/**
 * Search API client for unified search across entities, sources, and relations.
 */

// Types matching backend schemas
export type SearchResultType = "entity" | "source" | "relation";

export interface SearchFilters {
  query: string;
  types?: SearchResultType[];
  ui_category_id?: string[];
  source_kind?: string[];
  limit?: number;
  offset?: number;
}

export interface SearchResultBase {
  id: string;
  type: SearchResultType;
  title: string;
  snippet?: string;
  relevance_score?: number;
}

export interface EntitySearchResult extends SearchResultBase {
  type: "entity";
  slug: string;
  ui_category_id?: string;
  summary?: Record<string, string>;
}

export interface SourceSearchResult extends SearchResultBase {
  type: "source";
  kind: string;
  year?: number;
  authors?: string[];
  trust_level?: number;
}

export interface RelationSearchResult extends SearchResultBase {
  type: "relation";
  kind?: string;
  source_id: string;
  entity_ids: string[];
  direction?: string;
}

export type SearchResult =
  | EntitySearchResult
  | SourceSearchResult
  | RelationSearchResult;

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  limit: number;
  offset: number;
  entity_count: number;
  source_count: number;
  relation_count: number;
}

export interface SearchSuggestion {
  id: string;
  type: "entity" | "source";
  label: string;
  secondary?: string;
}

export interface SearchSuggestionsResponse {
  query: string;
  suggestions: SearchSuggestion[];
}

/**
 * Perform unified search across entities, sources, and relations.
 */
export function search(filters: SearchFilters): Promise<SearchResponse> {
  const params = new URLSearchParams();

  params.append("query", filters.query);

  if (filters.types) {
    filters.types.forEach(type => params.append("types", type));
  }

  if (filters.ui_category_id) {
    filters.ui_category_id.forEach(id => params.append("ui_category_id", id));
  }

  if (filters.source_kind) {
    filters.source_kind.forEach(kind => params.append("source_kind", kind));
  }

  if (filters.limit !== undefined) {
    params.append("limit", filters.limit.toString());
  }

  if (filters.offset !== undefined) {
    params.append("offset", filters.offset.toString());
  }

  return apiFetch(`/search?${params.toString()}`, {
    method: "POST",
  });
}

/**
 * Get autocomplete suggestions for search query.
 */
export function getSuggestions(
  query: string,
  types?: ("entity" | "source")[],
  limit?: number
): Promise<SearchSuggestionsResponse> {
  const params = new URLSearchParams();

  params.append("query", query);

  if (types) {
    types.forEach(type => params.append("types", type));
  }

  if (limit !== undefined) {
    params.append("limit", limit.toString());
  }

  return apiFetch(`/search/suggestions?${params.toString()}`, {
    method: "POST",
  });
}

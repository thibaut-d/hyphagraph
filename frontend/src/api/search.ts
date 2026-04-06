import { apiFetch } from "./client";
import {
  appendArrayParam,
  appendOptionalNumber,
  appendOptionalParam,
  buildQueryString,
  createSearchParams,
} from "./queryString";

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
  type: "entity" | "source" | "relation";
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
  const params = createSearchParams((query) => {
    appendOptionalParam(query, "query", filters.query);
    appendArrayParam(query, "types", filters.types);
    appendArrayParam(query, "ui_category_id", filters.ui_category_id);
    appendArrayParam(query, "source_kind", filters.source_kind);
    appendOptionalNumber(query, "limit", filters.limit);
    appendOptionalNumber(query, "offset", filters.offset);
  });

  return apiFetch(`/search/${buildQueryString(params)}`, {
    method: "POST",
  });
}

/**
 * Get autocomplete suggestions for search query.
 */
export function getSuggestions(
  query: string,
  types?: ("entity" | "source" | "relation")[],
  limit?: number,
  signal?: AbortSignal,
): Promise<SearchSuggestionsResponse> {
  const params = createSearchParams((params) => {
    appendOptionalParam(params, "query", query);
    appendArrayParam(params, "types", types);
    appendOptionalNumber(params, "limit", limit);
  });

  return apiFetch(`/search/suggestions${buildQueryString(params)}`, {
    method: "POST",
    signal,
  });
}

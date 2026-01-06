/**
 * Types for PubMed bulk search and import.
 */

export interface PubMedSearchResult {
  pmid: string;
  title: string;
  authors: string[];
  journal: string | null;
  year: number | null;
  doi: string | null;
  url: string;
}

export interface PubMedBulkSearchRequest {
  query?: string;  // Direct search query
  search_url?: string;  // Or PubMed search URL
  max_results: number;  // 1-100
}

export interface PubMedBulkSearchResponse {
  query: string;  // The actual query used
  total_results: number;  // Total results available in PubMed
  results: PubMedSearchResult[];  // Article metadata
  retrieved_count: number;  // Number of articles retrieved
}

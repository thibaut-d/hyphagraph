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

export interface PubMedBulkImportRequest {
  pmids: string[];  // List of PMIDs to import
}

export interface PubMedBulkImportResponse {
  total_requested: number;  // Number of PMIDs requested
  sources_created: number;  // Number of sources successfully created
  failed_pmids: string[];  // PMIDs that failed to import
  source_ids: string[];  // IDs of created sources
}

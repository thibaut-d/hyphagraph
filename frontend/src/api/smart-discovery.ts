import { apiFetch } from "./client";

export interface SmartDiscoveryRequest {
  entity_slugs: string[];
  max_results?: number;
  min_quality?: number;
  databases?: string[];
}

export interface SmartDiscoveryResult {
  pmid?: string | null;
  title: string;
  authors: string[];
  journal?: string | null;
  year?: number | null;
  doi?: string | null;
  url: string;
  trust_level: number;
  relevance_score: number;
  database: string;
  already_imported: boolean;
}

export interface SmartDiscoveryResponse {
  entity_slugs: string[];
  query_used: string;
  total_found: number;
  results: SmartDiscoveryResult[];
  databases_searched: string[];
}

export function smartDiscovery(request: SmartDiscoveryRequest): Promise<SmartDiscoveryResponse> {
  return apiFetch("/smart-discovery", {
    method: "POST",
    body: JSON.stringify({
      entity_slugs: request.entity_slugs,
      max_results: request.max_results || 20,
      min_quality: request.min_quality || 0.5,
      databases: request.databases || ["pubmed"],
    }),
  });
}

export interface BulkImportFromDiscoveryRequest {
  pmids: string[];
}

export interface BulkImportFromDiscoveryResponse {
  total_requested: number;
  sources_created: number;
  failed_pmids: string[];
  source_ids: string[];
}

export function bulkImportFromDiscovery(pmids: string[]): Promise<BulkImportFromDiscoveryResponse> {
  return apiFetch("/pubmed/bulk-import", {
    method: "POST",
    body: JSON.stringify({ pmids }),
  });
}

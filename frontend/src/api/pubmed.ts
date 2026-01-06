/**
 * API client for PubMed bulk search and import.
 */
import { apiFetch } from "./client";
import type {
  PubMedBulkSearchRequest,
  PubMedBulkSearchResponse,
  PubMedBulkImportRequest,
  PubMedBulkImportResponse,
} from "../types/pubmed";

/**
 * Search PubMed and retrieve article metadata for bulk import.
 *
 * POST /api/pubmed/bulk-search
 *
 * Supports:
 * - Direct search query (e.g., "CRISPR AND 2024[pdat]")
 * - PubMed search URL (e.g., "https://pubmed.ncbi.nlm.nih.gov/?term=...")
 *
 * @param request - Search parameters
 * @returns Search results with article metadata
 */
export async function bulkSearchPubMed(
  request: PubMedBulkSearchRequest
): Promise<PubMedBulkSearchResponse> {
  return apiFetch<PubMedBulkSearchResponse>("/api/pubmed/bulk-search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
}

/**
 * Batch import PubMed articles as sources.
 *
 * POST /api/pubmed/bulk-import
 *
 * Creates a source for each PMID with complete metadata.
 * Rate limited to 3 requests/second per NCBI guidelines.
 *
 * @param request - List of PMIDs to import
 * @returns Import result with created source IDs
 */
export async function bulkImportPubMed(
  request: PubMedBulkImportRequest
): Promise<PubMedBulkImportResponse> {
  return apiFetch<PubMedBulkImportResponse>("/api/pubmed/bulk-import", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
}

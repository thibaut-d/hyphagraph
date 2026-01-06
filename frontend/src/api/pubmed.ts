/**
 * API client for PubMed bulk search and import.
 */
import { apiFetch } from "./client";
import type {
  PubMedBulkSearchRequest,
  PubMedBulkSearchResponse,
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

/**
 * API client for knowledge extraction endpoints.
 *
 * Handles document upload, extraction, entity linking, and saving to graph.
 */
import { apiFetch } from "./client";
import type {
  DocumentUploadResponse,
  DocumentExtractionPreview,
  SaveExtractionRequest,
  SaveExtractionResult,
} from "../types/extraction";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Upload a document (PDF or TXT) to a source.
 *
 * POST /api/sources/{source_id}/upload-document
 *
 * @param sourceId - UUID of the source
 * @param file - File to upload (PDF or TXT)
 * @returns Upload result with text preview
 */
export async function uploadDocument(
  sourceId: string,
  file: File
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_BASE}/api/sources/${sourceId}/upload-document`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: formData,
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to upload document");
  }

  return response.json();
}

/**
 * Extract entities and relations from source's uploaded document.
 *
 * POST /api/sources/{source_id}/extract-from-document
 *
 * Prerequisites:
 * - Source must have document uploaded
 * - LLM service must be configured
 *
 * @param sourceId - UUID of the source
 * @returns Extraction preview with entities, relations, and link suggestions
 */
export async function extractFromDocument(
  sourceId: string
): Promise<DocumentExtractionPreview> {
  return apiFetch<DocumentExtractionPreview>(
    `/api/sources/${sourceId}/extract-from-document`,
    {
      method: "POST",
    }
  );
}

/**
 * Upload document AND extract knowledge in one step.
 *
 * POST /api/sources/{source_id}/upload-and-extract
 *
 * Combines:
 * 1. Document upload
 * 2. Text extraction
 * 3. Knowledge extraction (entities + relations)
 * 4. Entity linking suggestions
 *
 * @param sourceId - UUID of the source
 * @param file - File to upload (PDF or TXT)
 * @returns Extraction preview with entities, relations, and link suggestions
 */
export async function uploadAndExtract(
  sourceId: string,
  file: File
): Promise<DocumentExtractionPreview> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_BASE}/api/sources/${sourceId}/upload-and-extract`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: formData,
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to upload and extract");
  }

  return response.json();
}

/**
 * Fetch content from URL and extract knowledge.
 *
 * POST /api/sources/{source_id}/extract-from-url
 *
 * Supports:
 * - PubMed URLs (uses official NCBI API)
 * - General web pages (limited support)
 *
 * Combines:
 * 1. URL content fetching
 * 2. Text extraction
 * 3. Knowledge extraction (entities + relations)
 * 4. Entity linking suggestions
 *
 * @param sourceId - UUID of the source
 * @param url - URL to fetch and extract from
 * @returns Extraction preview with entities, relations, and link suggestions
 */
export async function extractFromUrl(
  sourceId: string,
  url: string
): Promise<DocumentExtractionPreview> {
  return apiFetch<DocumentExtractionPreview>(
    `/api/sources/${sourceId}/extract-from-url`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
    }
  );
}

/**
 * Save user-approved extracted knowledge to the graph.
 *
 * POST /api/sources/{source_id}/save-extraction
 *
 * Creates new entities, links to existing entities, and creates relations
 * based on user's decisions from the extraction preview.
 *
 * @param sourceId - UUID of the source
 * @param request - User-approved entities, links, and relations
 * @returns Result with counts of created/linked items
 */
export async function saveExtraction(
  sourceId: string,
  request: SaveExtractionRequest
): Promise<SaveExtractionResult> {
  return apiFetch<SaveExtractionResult>(
    `/api/sources/${sourceId}/save-extraction`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    }
  );
}

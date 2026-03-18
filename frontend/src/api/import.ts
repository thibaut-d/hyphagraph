/**
 * API client for bulk import endpoints.
 *
 * Two-step workflow:
 * 1. previewEntityImport — validate rows, get per-row status (no DB writes)
 * 2. executeEntityImport — write new entities to the knowledge graph
 */
import { apiFetch } from "./client";

export type ImportRowStatus = "new" | "duplicate" | "invalid";

export interface EntityImportPreviewRow {
  row: number;
  slug: string;
  summary_en: string | null;
  status: ImportRowStatus;
  error: string | null;
}

export interface ImportPreviewResult {
  rows: EntityImportPreviewRow[];
  total: number;
  new_count: number;
  duplicate_count: number;
  invalid_count: number;
}

export interface ImportResult {
  created: number;
  skipped_duplicates: number;
  failed: number;
  entity_ids: string[];
}

/**
 * Build a FormData object for a file upload with format field.
 */
function buildFormData(file: File, format: "csv" | "json"): FormData {
  const form = new FormData();
  form.append("file", file);
  form.append("format", format);
  return form;
}

/**
 * Validate an entity import file and return a per-row preview.
 * No data is written to the database.
 */
export async function previewEntityImport(
  file: File,
  format: "csv" | "json" = "csv"
): Promise<ImportPreviewResult> {
  const form = buildFormData(file, format);
  return apiFetch<ImportPreviewResult>("/api/import/entities/preview", {
    method: "POST",
    body: form,
  });
}

/**
 * Execute the bulk entity import, writing new entities to the DB.
 */
export async function executeEntityImport(
  file: File,
  format: "csv" | "json" = "csv"
): Promise<ImportResult> {
  const form = buildFormData(file, format);
  return apiFetch<ImportResult>("/api/import/entities", {
    method: "POST",
    body: form,
  });
}

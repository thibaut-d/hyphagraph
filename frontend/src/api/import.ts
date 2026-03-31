/**
 * API client for bulk import endpoints.
 *
 * Two-step workflow:
 * 1. previewEntityImport — validate rows, get per-row status (no DB writes)
 * 2. executeEntityImport — write new entities to the knowledge graph
 */
import { apiFetchFormData } from "./client";

export type ImportRowStatus = "new" | "duplicate" | "invalid";

export interface EntityImportPreviewRow {
  row: number;
  slug: string;
  summary_en: string | null;
  summary_fr: string | null;
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
  return apiFetchFormData<ImportPreviewResult>("/import/entities/preview", {
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
  return apiFetchFormData<ImportResult>("/import/entities", {
    method: "POST",
    body: form,
  });
}

// =============================================================================
// Source import
// =============================================================================

export type SourceImportFormat = "bibtex" | "ris" | "json";

export interface SourceImportPreviewRow {
  row: number;
  title: string;
  authors_display: string | null;
  year: number | null;
  url: string | null;
  status: ImportRowStatus;
  error: string | null;
}

export interface SourceImportPreviewResult {
  rows: SourceImportPreviewRow[];
  total: number;
  new_count: number;
  duplicate_count: number;
  invalid_count: number;
}

export interface SourceImportResult {
  created: number;
  skipped_duplicates: number;
  failed: number;
  source_ids: string[];
}

function buildSourceFormData(file: File, format: SourceImportFormat): FormData {
  const form = new FormData();
  form.append("file", file);
  form.append("format", format);
  return form;
}

/**
 * Validate a source import file (BibTeX/RIS/JSON) and return a per-row preview.
 * No data is written to the database.
 */
export async function previewSourceImport(
  file: File,
  format: SourceImportFormat = "bibtex"
): Promise<SourceImportPreviewResult> {
  const form = buildSourceFormData(file, format);
  return apiFetchFormData<SourceImportPreviewResult>("/import/sources/preview", {
    method: "POST",
    body: form,
  });
}

/**
 * Execute the bulk source import, writing new sources to the DB.
 */
export async function executeSourceImport(
  file: File,
  format: SourceImportFormat = "bibtex"
): Promise<SourceImportResult> {
  const form = buildSourceFormData(file, format);
  return apiFetchFormData<SourceImportResult>("/import/sources", {
    method: "POST",
    body: form,
  });
}

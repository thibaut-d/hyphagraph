import { apiFetch } from "./client";

export interface EntityTermWrite {
  term: string;
  language?: string | null;
  display_order?: number | null;
}

export interface EntityTermRead {
  id: string;
  entity_id: string;
  term: string;
  language: string | null;
  display_order: number | null;
  created_at: string;
}

export interface EntityTermBulkWrite {
  terms: EntityTermWrite[];
}

/**
 * List all terms/aliases for a specific entity.
 */
export function listEntityTerms(entityId: string): Promise<EntityTermRead[]> {
  return apiFetch(`/entities/${entityId}/terms`);
}

/**
 * Create a new term/alias for an entity.
 */
export function createEntityTerm(
  entityId: string,
  payload: EntityTermWrite
): Promise<EntityTermRead> {
  return apiFetch(`/entities/${entityId}/terms`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Update an existing term.
 */
export function updateEntityTerm(
  entityId: string,
  termId: string,
  payload: EntityTermWrite
): Promise<EntityTermRead> {
  return apiFetch(`/entities/${entityId}/terms/${termId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/**
 * Delete a term from an entity.
 */
export function deleteEntityTerm(
  entityId: string,
  termId: string
): Promise<void> {
  return apiFetch(`/entities/${entityId}/terms/${termId}`, {
    method: "DELETE",
  });
}

/**
 * Bulk replace all terms for an entity.
 * Deletes all existing terms and creates new ones.
 */
export function bulkUpdateEntityTerms(
  entityId: string,
  payload: EntityTermBulkWrite
): Promise<EntityTermRead[]> {
  return apiFetch(`/entities/${entityId}/terms-bulk`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

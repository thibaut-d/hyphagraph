/**
 * API client for the LLM-revision review queue.
 *
 * Draft revisions (status='draft') are created by bulk_creation_service when
 * created_with_llm is set.  Humans confirm or discard them here.
 */

import { apiFetch } from "./client";
import { buildQueryString, createSearchParams } from "./queryString";


export type RevisionKind = "entity" | "relation" | "source";


export interface DraftRevisionRead {
  id: string;
  revision_kind: RevisionKind;
  parent_id: string;
  created_with_llm: string | null;
  created_by_user_id: string | null;
  created_at: string;
  slug?: string | null;
  kind?: string | null;
  title?: string | null;
  status: string;
  llm_review_status?: string | null;
}


export interface DraftRevisionListResponse {
  items: DraftRevisionRead[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}


export interface DraftRevisionCounts {
  entity: number;
  relation: number;
  source: number;
  total: number;
}


export function listDraftRevisions(params?: {
  page?: number;
  page_size?: number;
  revision_kind?: RevisionKind;
}): Promise<DraftRevisionListResponse> {
  const searchParams = createSearchParams((q) => {
    if (params?.page !== undefined) q.set("page", String(params.page));
    if (params?.page_size !== undefined) q.set("page_size", String(params.page_size));
    if (params?.revision_kind) q.set("revision_kind", params.revision_kind);
  });
  return apiFetch(`/review/revisions${buildQueryString(searchParams)}`);
}


export function getDraftRevisionCounts(): Promise<DraftRevisionCounts> {
  return apiFetch("/review/revisions/counts");
}


export function confirmRevision(
  revision_kind: RevisionKind,
  revision_id: string,
): Promise<{ id: string; revision_kind: RevisionKind; status: string }> {
  return apiFetch(`/review/revisions/${revision_kind}/${revision_id}/confirm`, {
    method: "POST",
  });
}


export function discardRevision(
  revision_kind: RevisionKind,
  revision_id: string,
): Promise<{ id: string; revision_kind: RevisionKind; deleted: boolean }> {
  return apiFetch(`/review/revisions/${revision_kind}/${revision_id}`, {
    method: "DELETE",
  });
}

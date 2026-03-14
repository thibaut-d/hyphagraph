import { apiFetch } from "./client";
import { InferenceDetailRead, InferenceRead } from "../types/inference";
import { appendOptionalJson, buildQueryString, createSearchParams } from "./queryString";

export interface ScopeFilter {
  [key: string]: string | number | boolean;
}

export function getInferenceForEntity(
  entityId: string,
  scopeFilter?: ScopeFilter
): Promise<InferenceRead> {
  const params = createSearchParams((query) => {
    appendOptionalJson(query, "scope", scopeFilter);
  });
  return apiFetch(`/inferences/entity/${entityId}${buildQueryString(params)}`);
}

export function getInferenceDetailForEntity(
  entityId: string,
  scopeFilter?: ScopeFilter
): Promise<InferenceDetailRead> {
  const params = createSearchParams((query) => {
    appendOptionalJson(query, "scope", scopeFilter);
  });
  return apiFetch(`/inferences/entity/${entityId}/detail${buildQueryString(params)}`);
}

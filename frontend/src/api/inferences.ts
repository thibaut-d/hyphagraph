import { apiFetch } from "./client";
import { InferenceDetailRead, InferenceRead } from "../types/inference";
import { appendOptionalJson, buildQueryString, createSearchParams } from "./queryString";

export type ScopeFilterValue = string | number | boolean;

export interface ScopeFilter {
  [key: string]: ScopeFilterValue;
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

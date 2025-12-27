import { apiFetch } from "./client";
import { InferenceRead } from "../types/inference";

export interface ScopeFilter {
  [key: string]: string | number | boolean;
}

export function getInferenceForEntity(
  entityId: string,
  scopeFilter?: ScopeFilter
): Promise<InferenceRead> {
  const params = new URLSearchParams();

  if (scopeFilter && Object.keys(scopeFilter).length > 0) {
    params.set("scope", JSON.stringify(scopeFilter));
  }

  const queryString = params.toString();
  const url = queryString
    ? `/inferences/entity/${entityId}?${queryString}`
    : `/inferences/entity/${entityId}`;

  return apiFetch(url);
}

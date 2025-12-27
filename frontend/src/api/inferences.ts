import { apiFetch } from "./client";
import { InferenceRead } from "../types/inference";

export function getInferenceForEntity(entityId: string): Promise<InferenceRead> {
  return apiFetch(`/inferences/entity/${entityId}`);
}

import { apiFetch } from "./client";
import { EntityRead } from "../types/entity";

export function listEntities(): Promise<EntityRead[]> {
  return apiFetch("/entities");
}

export function getEntity(id: string): Promise<EntityRead> {
  return apiFetch(`/entities/${id}`);
}
import { apiFetch } from "./client";
import { SourceRead } from "../types/source";

export function listSources(): Promise<SourceRead[]> {
  return apiFetch("/sources");
}

export function getSource(id: string): Promise<SourceRead> {
  return apiFetch(`/sources/${id}`);
}
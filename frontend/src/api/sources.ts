import { apiFetch } from "./client";
import { SourceRead } from "../types/source";

export interface SourceWrite {
  kind: string;
  title: string;
  authors?: string[];
  year?: number;
  origin?: string;
  url: string;
  trust_level?: number;
  summary?: Record<string, string>;
  source_metadata?: Record<string, any>;
  created_with_llm?: string;
}

export function listSources(): Promise<SourceRead[]> {
  return apiFetch("/sources");
}

export function getSource(id: string): Promise<SourceRead> {
  return apiFetch(`/sources/${id}`);
}

export function createSource(payload: SourceWrite): Promise<SourceRead> {
  return apiFetch("/sources/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSource(id: string, payload: SourceWrite): Promise<SourceRead> {
  return apiFetch(`/sources/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteSource(id: string): Promise<void> {
  return apiFetch(`/sources/${id}`, {
    method: "DELETE",
  });
}
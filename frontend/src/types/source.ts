import type { JsonObject } from "./json";

export interface SourceRead {
  id: string;
  created_at: string;
  kind: string;
  title: string;
  authors?: string[] | null;
  year?: number | null;
  origin?: string | null;
  url: string;
  trust_level?: number | null;
  summary?: Record<string, string> | null;
  source_metadata?: JsonObject | null;
  created_with_llm?: string | null;
  created_by_user_id?: string | null;
  status: "draft" | "confirmed";
  llm_review_status?: string | null;
  document_format?: string | null;
  document_file_name?: string | null;
  document_extracted_at?: string | null;
  graph_usage_count?: number;
}

export interface SourceWrite {
  kind: string;
  title: string;
  authors?: string[] | null;
  year?: number | null;
  origin?: string | null;
  url: string;
  trust_level?: number | null;
  summary?: Record<string, string> | null;
  source_metadata?: JsonObject | null;
  created_with_llm?: string | null;
}

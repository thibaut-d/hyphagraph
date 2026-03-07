export interface SourceRead {
  id: string;
  created_at?: string;
  kind: string;
  title: string;
  authors?: string[] | null;
  year?: number | null;
  origin?: string | null;
  url?: string | null;
  trust_level?: number | null;
  trust?: number | null;
  summary?: Record<string, string> | null;
  source_metadata?: Record<string, string | number | boolean | null> | null;
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
  source_metadata?: Record<string, string | number | boolean | null> | null;
  created_with_llm?: string | null;
}

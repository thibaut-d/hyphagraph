export interface EntityRead {
  id: string;
  created_at: string;
  updated_at: string;
  slug: string;
  summary?: { [lang: string]: string } | null;
  ui_category_id?: string | null;
  created_with_llm?: string | null;
  created_by_user_id?: string | null;
  status: "draft" | "confirmed";
  llm_review_status?: string | null;
  consensus_level?: string | null;
}

export interface EntityRead {
  id: string;
  created_at: string;
  slug: string;
  summary?: { [lang: string]: string };
  ui_category_id?: string;
  consensus_level?: string | null;
}

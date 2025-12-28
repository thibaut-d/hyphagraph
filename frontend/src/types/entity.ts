export interface EntityRead {
  id: string;
  created_at: string;
  slug: string;
  summary?: { [lang: string]: string };
  ui_category_id?: string;
  kind?: string;
  label?: string;
  synonyms?: string[];
  ontology_ref?: string;
}
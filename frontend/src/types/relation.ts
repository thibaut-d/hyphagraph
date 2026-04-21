export interface RoleRead {
  id: string;
  relation_revision_id: string;
  entity_id: string;
  role_type: string;
  weight?: number | null;
  coverage?: number | null;
  entity_slug?: string | null;
  disagreement?: number | null;
}

export interface RelationRevisionRead {
  id: string;
  relation_id: string;
  kind?: string | null;
  direction?: string | null;
  confidence?: number | null;
  scope?: Record<string, unknown> | null;
  evidence_context?: Record<string, unknown> | null;
  notes?: string | Record<string, string> | null;
  created_with_llm?: string | null;
  created_by_user_id?: string | null;
  created_at: string;
  is_current: boolean;
  status: string;
  llm_review_status?: string | null;
  roles: RoleRead[];
}

export interface RelationRead {
  id: string;
  created_at: string;
  updated_at: string;
  source_id: string;
  source_title?: string | null;
  source_year?: number | null;
  kind?: string | null;
  direction?: string | null;
  confidence?: number | null;
  scope?: Record<string, unknown> | null;
  evidence_context?: Record<string, unknown> | null;
  notes?: string | Record<string, string> | null;
  created_with_llm?: string | null;
  status: "draft" | "confirmed";
  llm_review_status?: string | null;
  roles: RoleRead[];
}

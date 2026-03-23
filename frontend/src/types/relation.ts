export interface RoleRead {
  entity_id: string;
  role_type: string;
  weight?: number | null;
  coverage?: number | null;
  entity_slug?: string;  // Resolved entity slug for display
}

export interface RelationRevisionRead {
  id: string;
  relation_id: string;
  kind?: string | null;
  direction?: string | null;
  confidence?: number | null;
  scope?: Record<string, unknown> | null;
  notes?: string | Record<string, string> | null;
  created_with_llm?: string | null;
  created_by_user_id?: string | null;
  created_at: string;
  is_current: boolean;
  status: string;
  roles: RoleRead[];
}

export interface RelationRead {
  id: string;
  created_at?: string;
  source_id: string;
  kind?: string | null;
  direction?: string | null;
  confidence?: number | null;
  scope?: Record<string, unknown> | null;
  roles: RoleRead[];
  notes?: string | Record<string, string> | null;
  status?: "draft" | "confirmed";
}

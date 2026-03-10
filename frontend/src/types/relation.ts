export interface RoleRead {
  entity_id: string;
  role_type: string;
  weight?: number | null;
  coverage?: number | null;
  entity_slug?: string;  // Resolved entity slug for display
}

export interface RelationRead {
  id: string;
  created_at?: string;
  source_id: string;
  entity_id?: string;
  kind?: string | null;
  direction?: string | null;
  confidence?: number | null;
  scope?: Record<string, unknown> | null;
  roles: RoleRead[];
  notes?: string | Record<string, string> | null;
}

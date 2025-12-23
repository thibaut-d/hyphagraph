export interface RoleRead {
  entity_id: string;
  role_type: string;
}

export interface RelationRead {
  id: string;
  source_id: string;
  kind: string;
  direction: string;
  confidence: number;
  roles: RoleRead[];
  notes?: string;
}
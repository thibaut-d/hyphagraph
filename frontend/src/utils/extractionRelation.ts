import type { ExtractedRelation } from "../types/extraction";

function roleSignature(relation: ExtractedRelation): string {
  return (relation.roles ?? [])
    .map((role) => `${role.role_type}:${role.entity_slug}`)
    .sort()
    .join("|");
}

function pickRoleEntity(
  relation: ExtractedRelation,
  candidates: string[],
  fallbackIndex: number,
): string {
  const roles = relation.roles ?? [];

  if (roles.length === 0) {
    return "Unknown";
  }

  const matched = roles.find((role) => candidates.includes(role.role_type));
  if (matched?.entity_slug) {
    return matched.entity_slug;
  }

  return roles[fallbackIndex]?.entity_slug || roles[0]?.entity_slug || "Unknown";
}

export function getRelationKey(relation: ExtractedRelation): string {
  return [relation.relation_type, relation.text_span, roleSignature(relation)].join("||");
}

export function getRelationSubject(relation: ExtractedRelation): string {
  return pickRoleEntity(
    relation,
    ["subject", "agent", "biomarker", "measured_by", "study_group"],
    0,
  );
}

export function getRelationObject(relation: ExtractedRelation): string {
  return pickRoleEntity(
    relation,
    ["object", "target", "outcome", "population", "control_group", "condition"],
    1,
  );
}

export function getRelationDisplayRoles(relation: ExtractedRelation): Array<{ role: string; value: string }> {
  return (relation.roles ?? []).map((role) => ({
    role: role.role_type,
    value: role.entity_slug,
  }));
}

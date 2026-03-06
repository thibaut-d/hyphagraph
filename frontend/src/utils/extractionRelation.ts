import type { ExtractedRelation, ExtractedRole } from "../types/extraction";

function isRoleArray(roles: ExtractedRelation["roles"]): roles is ExtractedRole[] {
  return Array.isArray(roles);
}

function roleSignature(relation: ExtractedRelation): string {
  if (isRoleArray(relation.roles)) {
    return relation.roles
      .map((role) => `${role.role_type}:${role.entity_slug}`)
      .sort()
      .join("|");
  }

  return Object.entries(relation.roles)
    .map(([key, value]) => `${key}:${value}`)
    .sort()
    .join("|");
}

function pickRoleEntity(
  relation: ExtractedRelation,
  candidates: string[],
  fallbackIndex: number,
): string {
  if (!isRoleArray(relation.roles)) {
    for (const candidate of candidates) {
      const value = relation.roles[candidate];
      if (value) {
        return value;
      }
    }

    return Object.values(relation.roles)[fallbackIndex] || Object.values(relation.roles)[0] || "Unknown";
  }

  if (relation.roles.length === 0) {
    return "Unknown";
  }

  const matched = relation.roles.find((role) => candidates.includes(role.role_type));
  if (matched?.entity_slug) {
    return matched.entity_slug;
  }

  return relation.roles[fallbackIndex]?.entity_slug || relation.roles[0]?.entity_slug || "Unknown";
}

export function getRelationKey(relation: ExtractedRelation): string {
  return [relation.relation_type, relation.text_span, roleSignature(relation)].join("||");
}

export function getRelationSubject(relation: ExtractedRelation): string {
  if (relation.subject_slug) {
    return relation.subject_slug;
  }

  return pickRoleEntity(
    relation,
    ["subject", "agent", "biomarker", "measured_by", "study_group"],
    0,
  );
}

export function getRelationObject(relation: ExtractedRelation): string {
  if (relation.object_slug) {
    return relation.object_slug;
  }

  return pickRoleEntity(
    relation,
    ["object", "target", "outcome", "population", "control_group", "condition"],
    1,
  );
}

export function getRelationDisplayRoles(relation: ExtractedRelation): Array<{ role: string; value: string }> {
  if (isRoleArray(relation.roles)) {
    return relation.roles.map((role) => ({
      role: role.role_type,
      value: role.entity_slug,
    }));
  }

  return Object.entries(relation.roles).map(([role, value]) => ({
    role,
    value,
  }));
}

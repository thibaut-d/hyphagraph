import type { RelationRead, RoleRead } from "../types/relation";

const DIRECTION_LABELS: Record<string, string> = {
  supports: "Supports",
  positive: "Supports",
  contradicts: "Contradicts",
  negative: "Contradicts",
  neutral: "Mixed or neutral",
  mixed: "Mixed or neutral",
};

export const SCOPE_FILTER_SUGGESTIONS = [
  { key: "population", label: "Population", example: "Adults" },
  { key: "condition", label: "Condition", example: "Migraine" },
  { key: "dosage", label: "Dosage", example: "Low dose" },
  { key: "tissue", label: "Tissue", example: "Liver" },
  { key: "timeframe", label: "Timeframe", example: "12 weeks" },
];

function sortRolesForDisplay(roles: RoleRead[]): RoleRead[] {
  const roleOrder: Record<string, number> = { subject: 0, object: 1 };
  return [...roles].sort((a, b) => (roleOrder[a.role_type] ?? 2) - (roleOrder[b.role_type] ?? 2));
}

function humanizeToken(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (char) => char.toUpperCase());
}

function formatRoleSummary(role: RoleRead): string {
  return `${role.entity_slug || role.entity_id} (${humanizeToken(role.role_type)})`;
}

export function normalizeRelationDirection(direction?: string | null): "supports" | "contradicts" | "neutral" {
  if (direction === "supports" || direction === "positive") {
    return "supports";
  }
  if (direction === "contradicts" || direction === "negative") {
    return "contradicts";
  }
  return "neutral";
}

export function formatDirectionLabel(direction?: string | null): string {
  return DIRECTION_LABELS[direction || "neutral"] || humanizeToken(direction || "neutral");
}

export function formatRelationClaim(relation: RelationRead, fallbackKind: string): string {
  const sortedRoles = sortRolesForDisplay(relation.roles);
  const subject = sortedRoles.find((role) => role.role_type === "subject");
  const object = sortedRoles.find((role) => role.role_type === "object");
  const kind = relation.kind || fallbackKind;
  const kindLower = kind.toLowerCase();

  if (subject?.entity_slug && object?.entity_slug) {
    if (kindLower.includes("treat")) {
      return `${subject.entity_slug} treats ${object.entity_slug}`;
    }
    if (kindLower.includes("biomarker")) {
      return `${subject.entity_slug} is a biomarker for ${object.entity_slug}`;
    }
    if (kindLower.includes("affect") || kindLower.includes("population")) {
      return `${subject.entity_slug} affects ${object.entity_slug}`;
    }
    if (kindLower.includes("cause")) {
      return `${subject.entity_slug} causes ${object.entity_slug}`;
    }
    if (kindLower.includes("correlate")) {
      return `${subject.entity_slug} correlates with ${object.entity_slug}`;
    }
    return `${subject.entity_slug} ${kind} ${object.entity_slug}`;
  }

  if (sortedRoles.length > 0) {
    return sortedRoles.map(formatRoleSummary).join(" -> ");
  }

  return humanizeToken(kind);
}

export function formatRelationContext(
  relation: Pick<RelationRead, "scope" | "notes">,
): string[] {
  const parts: string[] = [];

  if (relation.scope && Object.keys(relation.scope).length > 0) {
    const scopeSummary = Object.entries(relation.scope)
      .slice(0, 2)
      .map(([key, value]) => `${humanizeToken(key)}: ${String(value)}`)
      .join(" • ");
    parts.push(scopeSummary);
  }

  if (relation.notes) {
    const notesValue =
      typeof relation.notes === "string"
        ? relation.notes
        : Object.values(relation.notes)
            .filter((value): value is string => Boolean(value))
            .join(" ");
    const compactNotes = notesValue.trim();
    if (compactNotes) {
      parts.push(compactNotes.length > 120 ? `${compactNotes.slice(0, 117)}...` : compactNotes);
    }
  }

  return parts;
}

export function formatScopeFilterLabel(key: string, value: string): string {
  return `${humanizeToken(key)}: ${value}`;
}

export function formatScopeFilterOptionLabel(key: string): string {
  const suggestion = SCOPE_FILTER_SUGGESTIONS.find((item) => item.key === key);
  return suggestion?.label || humanizeToken(key);
}

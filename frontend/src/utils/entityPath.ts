export interface EntityPathInput {
  id?: string | null;
  slug?: string | null;
}

export function entityPath(entity: EntityPathInput): string {
  const ref = entity.slug || entity.id;
  if (!ref) {
    return "/entities";
  }
  return `/entities/${ref}`;
}

export function entitySubpath(entity: EntityPathInput, suffix: string): string {
  return `${entityPath(entity)}${suffix.startsWith("/") ? suffix : `/${suffix}`}`;
}

export function slugifyInput(
  value: string,
  options: { preserveTrailingSeparator?: boolean } = {},
): string {
  const slug = value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-+/g, "");

  if (options.preserveTrailingSeparator) {
    return slug;
  }

  return slug.replace(/-+$/g, "");
}

/**
 * Resolves an i18n label to the appropriate language.
 *
 * @param label - Fallback label (usually English)
 * @param labelI18n - Optional i18n dictionary with language codes as keys
 * @param language - Current language code (e.g., 'en', 'fr')
 * @returns The label in the requested language, or fallback
 */
export function resolveLabel(
  label: string | undefined,
  labelI18n: Record<string, string> | undefined,
  language: string
): string {
  const fallback = label ?? "";

  if (!labelI18n) {
    return fallback;
  }

  // Try exact language match
  if (labelI18n[language]) {
    return labelI18n[language];
  }

  // Try language without region (e.g., 'en' from 'en-US')
  const baseLanguage = language.split("-")[0];
  if (labelI18n[baseLanguage]) {
    return labelI18n[baseLanguage];
  }

  // Fallback to original label
  return fallback;
}

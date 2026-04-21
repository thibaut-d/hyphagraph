import type { ExtractedEntity } from "../types/extraction";

function humanizeSlug(slug: string): string {
  return slug
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (char) => char.toUpperCase());
}

function looksLikeSentence(value: string): boolean {
  const normalized = value.trim();
  if (!normalized) {
    return false;
  }

  const lower = normalized.toLowerCase();
  const wordCount = normalized.split(/\s+/).length;

  return (
    wordCount > 6 ||
    /[.!?;:]/.test(normalized) ||
    /\b(is|are|was|were|can|could|should|may|might|helps?|improves?|causes?)\b/.test(lower)
  );
}

export function getExtractedEntityDisplayLabel(entity: ExtractedEntity): string {
  const textSpan = entity.text_span?.trim();
  if (textSpan && !looksLikeSentence(textSpan)) {
    return textSpan;
  }

  return humanizeSlug(entity.slug);
}

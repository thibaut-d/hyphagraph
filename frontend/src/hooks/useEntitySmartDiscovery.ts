import { useState } from "react";
import { useTranslation } from "react-i18next";

import { smartSuggestEntities, prefillEntity, createEntity } from "../api/entities";
import { bulkUpdateEntityTerms, type EntityTermWrite } from "../api/entityTerms";
import type { EntityPrefillDraft } from "../api/entities";

export type SmartDiscoveryPhase = "configure" | "review" | "creating" | "done";

export interface UseEntitySmartDiscoveryResult {
  phase: SmartDiscoveryPhase;
  query: string;
  setQuery: (q: string) => void;
  count: number;
  setCount: (n: number) => void;
  suggesting: boolean;
  suggestError: string | null;
  terms: string[];
  newTerm: string;
  setNewTerm: (t: string) => void;
  handleSuggest: () => Promise<void>;
  handleAddTerm: () => void;
  handleRemoveTerm: (term: string) => void;
  handleSmartCreate: () => Promise<void>;
  handleBack: () => void;
  doneCount: number;
  totalCount: number;
  createdCount: number;
  failedTerms: string[];
  reset: () => void;
}

function buildTermsPayload(draft: EntityPrefillDraft): EntityTermWrite[] {
  const displayNameTerms: EntityTermWrite[] = Object.entries(draft.display_names)
    .map(([language, value], index) => ({
      term: value.trim(),
      language: language || null,
      display_order: index,
      is_display_name: true,
    }))
    .filter((t) => t.term.length > 0);

  const aliasTerms: EntityTermWrite[] = draft.aliases
    .map((alias, index) => ({
      term: alias.term.trim(),
      language: alias.language || null,
      display_order: displayNameTerms.length + index,
      is_display_name: false,
      term_kind: alias.term_kind,
    }))
    .filter(
      (alias) =>
        alias.term.length > 0 &&
        !displayNameTerms.some(
          (dn) => dn.term === alias.term && dn.language === (alias.language || null)
        )
    );

  return [...displayNameTerms, ...aliasTerms];
}

export function useEntitySmartDiscovery(): UseEntitySmartDiscoveryResult {
  const { i18n } = useTranslation();
  const userLanguage = (i18n.language || "en").split("-")[0].slice(0, 2);

  const [phase, setPhase] = useState<SmartDiscoveryPhase>("configure");
  const [query, setQuery] = useState("");
  const [count, setCount] = useState(10);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);
  const [terms, setTerms] = useState<string[]>([]);
  const [newTerm, setNewTerm] = useState("");

  const [doneCount, setDoneCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [createdCount, setCreatedCount] = useState(0);
  const [failedTerms, setFailedTerms] = useState<string[]>([]);

  const handleSuggest = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setSuggesting(true);
    setSuggestError(null);
    try {
      const response = await smartSuggestEntities({
        query: trimmed,
        count,
        user_language: userLanguage,
      });
      setTerms(response.terms);
      setPhase("review");
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to suggest entities";
      setSuggestError(message);
    } finally {
      setSuggesting(false);
    }
  };

  const handleAddTerm = () => {
    const trimmed = newTerm.trim();
    if (!trimmed) return;
    const alreadyPresent = terms.some(
      (t) => t.toLowerCase() === trimmed.toLowerCase()
    );
    if (!alreadyPresent) {
      setTerms((current) => [...current, trimmed]);
    }
    setNewTerm("");
  };

  const handleRemoveTerm = (term: string) => {
    setTerms((current) => current.filter((t) => t !== term));
  };

  const handleBack = () => {
    setPhase("configure");
    setSuggestError(null);
  };

  const handleSmartCreate = async () => {
    if (terms.length === 0) return;

    const total = terms.length;
    setTotalCount(total);
    setDoneCount(0);
    setCreatedCount(0);
    setFailedTerms([]);
    setPhase("creating");

    let created = 0;
    const failed: string[] = [];

    for (const term of terms) {
      try {
        const draft = await prefillEntity({ term, user_language: userLanguage });
        const summary = Object.keys(draft.summary).length > 0 ? draft.summary : undefined;
        const entity = await createEntity({
          slug: draft.slug,
          summary,
          ui_category_id: draft.ui_category_id ?? undefined,
        });
        const termsPayload = buildTermsPayload(draft);
        if (termsPayload.length > 0) {
          await bulkUpdateEntityTerms(entity.id, { terms: termsPayload });
        }
        created++;
      } catch {
        failed.push(term);
      }
      setDoneCount((n) => n + 1);
    }

    setCreatedCount(created);
    setFailedTerms(failed);
    setPhase("done");
  };

  const reset = () => {
    setPhase("configure");
    setQuery("");
    setCount(10);
    setSuggesting(false);
    setSuggestError(null);
    setTerms([]);
    setNewTerm("");
    setDoneCount(0);
    setTotalCount(0);
    setCreatedCount(0);
    setFailedTerms([]);
  };

  return {
    phase,
    query,
    setQuery,
    count,
    setCount,
    suggesting,
    suggestError,
    terms,
    newTerm,
    setNewTerm,
    handleSuggest,
    handleAddTerm,
    handleRemoveTerm,
    handleBack,
    handleSmartCreate,
    doneCount,
    totalCount,
    createdCount,
    failedTerms,
    reset,
  };
}


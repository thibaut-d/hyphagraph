import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { createSource, SourceWrite, extractMetadataFromUrl } from "../api/sources";
import { invalidateSourceFilterCache } from "../utils/cacheUtils";
import { useAsyncAction } from "./useAsyncAction";
import { useValidationMessage } from "./useValidationMessage";
import type { JsonObject } from "../types/json";

type ValidationField = "title" | "url";

export interface QualityBadge {
  label: string;
  color: "success" | "info" | "warning" | "error";
  description: string;
}

export function getQualityBadge(value: number): QualityBadge {
  if (value >= 0.9)
    return {
      label: "Very High Quality",
      color: "success",
      description: "Systematic Review / Meta-analysis (GRADE ⊕⊕⊕⊕)",
    };
  if (value >= 0.75)
    return {
      label: "High Quality",
      color: "success",
      description: "RCT / Cohort Study (GRADE ⊕⊕⊕⊕ or ⊕⊕⊕◯)",
    };
  if (value >= 0.65)
    return {
      label: "Moderate Quality",
      color: "info",
      description: "Case-Control Study (GRADE ⊕⊕⊕◯)",
    };
  if (value >= 0.5)
    return {
      label: "Low Quality",
      color: "warning",
      description: "Case Series / Observational (GRADE ⊕⊕◯◯)",
    };
  if (value >= 0.3)
    return {
      label: "Very Low Quality",
      color: "warning",
      description: "Case Report / Expert Opinion (GRADE ⊕◯◯◯)",
    };
  return {
    label: "Anecdotal",
    color: "error",
    description: "Anecdotal evidence / Opinion",
  };
}

export function useCreateSourceForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // Form state
  const [kind, setKind] = useState("article");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [authors, setAuthors] = useState("");
  const [year, setYear] = useState("");
  const [origin, setOrigin] = useState("");
  const [trustLevel, setTrustLevel] = useState("0.5");
  const [summaryEn, setSummaryEn] = useState("");
  const [summaryFr, setSummaryFr] = useState("");
  const [sourceMetadata, setSourceMetadata] = useState<JsonObject | null>(null);

  const {
    setValidationMessage,
    clearValidationMessage: clearError,
    getFieldError,
    hasFieldError,
  } = useValidationMessage<ValidationField>();
  const [submitError, setSubmitError] = useState<string | null>(null);

  // UI state
  const [extractError, setExtractError] = useState<string | null>(null);
  const [autofilled, setAutofilled] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const { isRunning: extracting, run: runMetadataExtraction } = useAsyncAction(setExtractError);
  const { isRunning: loading, run: runCreateSource } = useAsyncAction(setSubmitError);

  const handleExtractMetadata = async () => {
    if (!url.trim()) {
      setExtractError(t("create_source.url_required", "URL is required"));
      return;
    }

    setAutofilled(false);
    const result = await runMetadataExtraction(async () => {
      const metadata = await extractMetadataFromUrl(url.trim());

      if (metadata.title) setTitle(metadata.title);
      if (metadata.kind) setKind(metadata.kind);
      if (metadata.authors && metadata.authors.length > 0) {
        setAuthors(metadata.authors.join(", "));
      }
      if (metadata.year) setYear(metadata.year.toString());
      if (metadata.origin) setOrigin(metadata.origin);
      if (metadata.trust_level !== undefined && metadata.trust_level !== null) {
        setTrustLevel(metadata.trust_level.toString());
      }
      if (metadata.summary_en) setSummaryEn(metadata.summary_en);
      if (metadata.summary_fr) setSummaryFr(metadata.summary_fr);
      if (metadata.source_metadata) setSourceMetadata(metadata.source_metadata);

      setAutofilled(true);
      setExtractError(null);
    }, t("create_source.extract_error", "Failed to extract metadata from URL"));

    if (!result.ok) return;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setSubmitError(null);

    if (!title.trim()) {
      setValidationMessage(t("create_source.title_required", "Title is required"), "title");
      return;
    }
    if (!url.trim()) {
      setValidationMessage(t("create_source.url_required", "URL is required"), "url");
      return;
    }

    const result = await runCreateSource(async () => {
      const summary: Record<string, string> = {};
      if (summaryEn.trim()) summary.en = summaryEn.trim();
      if (summaryFr.trim()) summary.fr = summaryFr.trim();

      const authorsList = authors
        .split(",")
        .map((a) => a.trim())
        .filter((a) => a.length > 0);

      const payload: SourceWrite = {
        kind,
        title: title.trim(),
        url: url.trim(),
        authors: authorsList.length > 0 ? authorsList : undefined,
        year: year.trim() ? parseInt(year.trim(), 10) : undefined,
        origin: origin.trim() || undefined,
        trust_level: parseFloat(trustLevel),
        summary: Object.keys(summary).length > 0 ? summary : undefined,
        source_metadata: sourceMetadata || undefined,
      };

      const created = await createSource(payload);
      invalidateSourceFilterCache();
      navigate(`/sources/${created.id}`);
    }, t("common.error", "An error occurred"));

    if (!result.ok) return;
  };

  return {
    // Form values
    kind, setKind,
    title, setTitle,
    url, setUrl,
    authors, setAuthors,
    year, setYear,
    origin, setOrigin,
    trustLevel, setTrustLevel,
    summaryEn, setSummaryEn,
    summaryFr, setSummaryFr,
    sourceMetadata,
    // Validation
    getFieldError,
    hasFieldError,
    clearError,
    // Status
    autofilled,
    showAdvanced, setShowAdvanced,
    extracting,
    loading,
    extractError,
    submitError,
    // Derived
    qualityBadge: getQualityBadge(parseFloat(trustLevel)),
    // Handlers
    handleExtractMetadata,
    handleSubmit,
  };
}

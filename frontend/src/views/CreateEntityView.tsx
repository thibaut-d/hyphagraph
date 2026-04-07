import { useState, useEffect, useMemo } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Typography,
  Paper,
  Stack,
  TextField,
  Button,
  Box,
  IconButton,
  Alert,
  Autocomplete,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  CircularProgress,
  Link,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DeleteIcon from "@mui/icons-material/Delete";

import {
  createEntity,
  EntityWrite,
  getEntityFilterOptions,
  EntityFilterOptions,
  prefillEntity,
  type EntityPrefillDraft,
} from "../api/entities";
import { bulkUpdateEntityTerms, type EntityTermWrite } from "../api/entityTerms";
import { search as searchApi, type EntitySearchResult } from "../api/search";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { useValidationMessage } from "../hooks/useValidationMessage";
import { useNotification } from "../notifications/NotificationContext";
import { entityPath } from "../utils/entityPath";
import { slugifyInput } from "../utils/slug";

type ValidationField = "slug";
type AliasDraft = {
  id: string;
  term: string;
  language: string;
  term_kind: "alias" | "abbreviation" | "brand";
};
type SummaryMap = Record<string, string>;
type EntityDraftValues = Pick<
  EntityPrefillDraft,
  "slug" | "display_names" | "summary" | "aliases" | "ui_category_id"
>;

const LANGUAGE_OPTIONS = [
  { code: "", label: "International" },
  { code: "en", label: "English" },
  { code: "fr", label: "French" },
  { code: "es", label: "Spanish" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "zh", label: "Chinese" },
  { code: "ja", label: "Japanese" },
  { code: "la", label: "Latin" },
];

const LANGUAGE_SELECT_SX = {
  "& .MuiSelect-select": {
    minWidth: 0,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
};

const LANGUAGE_MENU_PROPS = {
  PaperProps: {
    sx: {
      "& .MuiMenuItem-root": {
        whiteSpace: "normal",
      },
    },
  },
};

function createAliasDraft(): AliasDraft {
  return {
    id: globalThis.crypto?.randomUUID?.() ?? `alias-${Date.now()}-${Math.random()}`,
    term: "",
    language: "",
    term_kind: "alias",
  };
}

function normalizeUiLanguage(language: string): string {
  const normalized = language.split("-")[0]?.toLowerCase() ?? "en";
  return /^[a-z]{2}$/.test(normalized) ? normalized : "en";
}

function FormSection({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack spacing={2}>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {description}
          </Typography>
        </Box>
        {children}
      </Stack>
    </Paper>
  );
}

export function CreateEntityView() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { showError } = useNotification();
  const currentLanguage = i18n.language || "en";
  const userLanguage = normalizeUiLanguage(currentLanguage);

  const [lookupTerm, setLookupTerm] = useState("");
  const [lookupResults, setLookupResults] = useState<EntitySearchResult[]>([]);
  const [lookupSearchedTerm, setLookupSearchedTerm] = useState("");
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupHasSearched, setLookupHasSearched] = useState(false);
  const [aiPrefillLoading, setAiPrefillLoading] = useState(false);
  const [prefillError, setPrefillError] = useState<string | null>(null);
  const [slug, setSlug] = useState("");
  const [displayNames, setDisplayNames] = useState<SummaryMap>({});
  const [activeDisplayNameLanguage, setActiveDisplayNameLanguage] = useState("");
  const [summaries, setSummaries] = useState<SummaryMap>({});
  const [activeSummaryLanguage, setActiveSummaryLanguage] = useState(
    currentLanguage === "fr" ? "fr" : "en",
  );
  const [uiCategoryId, setUiCategoryId] = useState<string | null>(null);
  const [aliases, setAliases] = useState<AliasDraft[]>([]);
  const [filterOptions, setFilterOptions] = useState<EntityFilterOptions | null>(null);
  const {
    setValidationMessage,
    clearValidationMessage: clearError,
    getFieldError,
    hasFieldError,
  } = useValidationMessage<ValidationField>();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { isRunning: loading, run } = useAsyncAction(setSubmitError);

  // Fetch UI category options
  useEffect(() => {
    getEntityFilterOptions()
      .then(setFilterOptions)
      .catch((error) => {
        const message = t(
          "create_entity.filter_options_error",
          "Failed to load entity category options"
        );
        setSubmitError(message);
        showError(error);
      });
  }, [showError, t]);

  // Extract category options with current language labels
  const categoryOptions = useMemo(() => {
    // Validate filterOptions and ui_categories exist before accessing
    if (!filterOptions?.ui_categories) return [];

    return filterOptions.ui_categories.map(cat => ({
      id: cat.id,
      // Safe access to nested label properties with fallbacks
      label: (cat.label?.[currentLanguage as keyof typeof cat.label] as string | undefined) ||
             cat.label?.en ||
             cat.id
    }));
  }, [filterOptions, i18n.language]);

  const getLanguageLabel = (language: string): string => {
    const option = LANGUAGE_OPTIONS.find((candidate) => candidate.code === language);
    return option ? t(`entityTerms.lang_${option.code}`, option.label) : language.toUpperCase();
  };

  const applyDraftValues = (draft: EntityDraftValues) => {
    const nextSlug = slugifyInput(draft.slug);
    if (nextSlug) {
      setSlug(nextSlug);
      clearError("slug");
    }
    setDisplayNames(draft.display_names);
    setSummaries(draft.summary);
    setUiCategoryId(draft.ui_category_id ?? null);
    setAliases(
      draft.aliases.map((alias) => ({
        id: createAliasDraft().id,
        term: alias.term,
        language: alias.language ?? "",
        term_kind: alias.term_kind ?? "alias",
      })),
    );

    if (Object.prototype.hasOwnProperty.call(draft.display_names, "")) {
      setActiveDisplayNameLanguage("");
    } else {
      setActiveDisplayNameLanguage(
        draft.display_names[userLanguage] !== undefined
          ? userLanguage
          : Object.keys(draft.display_names)[0] ?? "",
      );
    }

    setActiveSummaryLanguage(
      draft.summary[userLanguage] !== undefined
        ? userLanguage
        : Object.keys(draft.summary)[0] ?? userLanguage,
    );
  };

  const handleLookup = async () => {
    const term = lookupTerm.trim();
    setLookupError(null);
    setPrefillError(null);
    setLookupHasSearched(false);
    if (!term) {
      setLookupError(t("create_entity.lookup_required", "Enter a term to search first."));
      return;
    }

    setLookupLoading(true);
    try {
      const response = await searchApi({
        query: term,
        types: ["entity"],
        limit: 5,
      });
      setLookupResults(
        response.results.filter((result): result is EntitySearchResult => result.type === "entity"),
      );
      setLookupSearchedTerm(term);
      setLookupHasSearched(true);
    } catch (error) {
      setLookupError(
        t("create_entity.lookup_error", "Failed to search existing entities."),
      );
      showError(error);
    } finally {
      setLookupLoading(false);
    }
  };

  const handleSimplePrefill = () => {
    const term = lookupSearchedTerm || lookupTerm.trim();
    if (!term) {
      setPrefillError(t("create_entity.lookup_required", "Enter a term to search first."));
      return;
    }
    applyDraftValues({
      slug: slugifyInput(term),
      display_names: { [userLanguage]: term },
      summary: {},
      aliases: [],
      ui_category_id: null,
    });
  };

  const handleAiPrefill = async () => {
    const term = lookupSearchedTerm || lookupTerm.trim();
    setPrefillError(null);
    if (!term) {
      setPrefillError(t("create_entity.lookup_required", "Enter a term to search first."));
      return;
    }

    setAiPrefillLoading(true);
    try {
      const draft = await prefillEntity({
        term,
        user_language: userLanguage,
      });
      applyDraftValues(draft);
    } catch (error) {
      setPrefillError(
        t(
          "create_entity.ai_prefill_error",
          "AI prefill failed. Check that the API key is configured, then try again.",
        ),
      );
      showError(error);
    } finally {
      setAiPrefillLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setSubmitError(null);
    const normalizedSlug = slugifyInput(slug);
    if (!normalizedSlug) {
      setValidationMessage(t("create_entity.slug_required", "Slug is required"), "slug");
      return;
    }
    const SLUG_PATTERN = /^[a-z][a-z0-9-]*$/;
    if (
      normalizedSlug.length < 3 ||
      normalizedSlug.length > 100 ||
      !SLUG_PATTERN.test(normalizedSlug)
    ) {
      setValidationMessage(t("create_entity.slug_format", "Slug must be 3–100 lowercase letters, digits, or hyphens, starting with a letter"), "slug");
      return;
    }

    const result = await run(async () => {
      const summary = Object.fromEntries(
        Object.entries(summaries)
          .map(([language, value]) => [language, value.trim()])
          .filter(([, value]) => value.length > 0),
      );

      const payload: EntityWrite = {
        slug: normalizedSlug,
        summary: Object.keys(summary).length > 0 ? summary : undefined,
        ui_category_id: uiCategoryId || undefined,
      };

      const created = await createEntity(payload);

      const displayNameTerms: EntityTermWrite[] = Object.entries(displayNames)
        .map(([language, value], index) => ({
          term: value.trim(),
          language: language || null,
          display_order: index,
          is_display_name: true,
        }))
        .filter((term) => term.term.length > 0);

      const aliasTerms: EntityTermWrite[] = aliases
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
              (displayNameTerm) =>
                displayNameTerm.term === alias.term &&
                displayNameTerm.language === (alias.language || null),
            ),
        );

      const termsPayload = [...displayNameTerms, ...aliasTerms];

      if (termsPayload.length > 0) {
        try {
          await bulkUpdateEntityTerms(created.id, { terms: termsPayload });
        } catch (error) {
          showError(
            new Error(
              t(
                "create_entity.alias_save_error",
                "Entity created, but failed to save aliases.",
              ),
            ),
          );
        }
      }

      // Navigate to the created entity
      navigate(entityPath(created));
    }, t("common.error", "An error occurred"));

    if (!result.ok) {
      return;
    }
  };

  const updateAlias = (id: string, patch: Partial<AliasDraft>) => {
    setAliases((current) =>
      current.map((alias) => (alias.id === id ? { ...alias, ...patch } : alias)),
    );
  };

  const addAliasRow = () => {
    setAliases((current) => [...current, createAliasDraft()]);
  };

  const removeAliasRow = (id: string) => {
    setAliases((current) => current.filter((alias) => alias.id !== id));
  };

  const filledSummaryLanguages = Object.entries(summaries)
    .filter(([, value]) => value.trim().length > 0)
    .map(([language]) => language);
  const filledDisplayNameLanguages = Object.entries(displayNames)
    .filter(([, value]) => value.trim().length > 0)
    .map(([language]) => language);

  return (
    <Paper sx={{ p: 4, maxWidth: 800, mx: "auto" }}>
      <Stack spacing={3}>
        {/* Header with back button */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <IconButton onClick={() => navigate("/entities")} size="small">
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {t("create_entity.title", "Create Entity")}
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary">
          {t(
            "create_entity.description",
            "Create a new entity in the knowledge graph. The slug is a unique identifier for this entity."
          )}
        </Typography>

        {/* Error message */}
        {submitError && <Alert severity="error">{submitError}</Alert>}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
            <FormSection
              title={t("create_entity.lookup_title", "Check before creating")}
              description={t(
                "create_entity.lookup_description",
                "Search existing entity slugs and terms first. If nothing matches, prefill the form from the term.",
              )}
            >
              <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                <TextField
                  label={t("create_entity.lookup_term", "Entity term")}
                  value={lookupTerm}
                  onChange={(e) => {
                    setLookupTerm(e.target.value);
                    setLookupError(null);
                    setPrefillError(null);
                  }}
                  disabled={loading || lookupLoading || aiPrefillLoading}
                  fullWidth
                  helperText={t(
                    "create_entity.lookup_help",
                    "Example: Paracetamol, Doliprane, acetaminophen",
                  )}
                />
                <Button
                  type="button"
                  variant="contained"
                  onClick={handleLookup}
                  disabled={loading || lookupLoading || aiPrefillLoading}
                  sx={{ minWidth: { sm: 160 } }}
                >
                  {lookupLoading ? (
                    <CircularProgress color="inherit" size={20} />
                  ) : (
                    t("create_entity.lookup_action", "Search")
                  )}
                </Button>
              </Stack>

              {lookupError && <Alert severity="error">{lookupError}</Alert>}
              {prefillError && <Alert severity="error">{prefillError}</Alert>}

              {lookupHasSearched && lookupResults.length > 0 && (
                <Alert severity="warning">
                  <Stack spacing={1}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {t(
                        "create_entity.lookup_existing_found",
                        "Possible existing entities found. Open the existing entity instead of creating a duplicate.",
                      )}
                    </Typography>
                    <Stack spacing={0.5}>
                      {lookupResults.map((result) => (
                        <Link
                          key={result.id}
                          component={RouterLink}
                          to={entityPath(result)}
                          underline="hover"
                        >
                          {result.slug}
                        </Link>
                      ))}
                    </Stack>
                  </Stack>
                </Alert>
              )}

              {lookupHasSearched && !lookupLoading && !lookupError && lookupResults.length === 0 && (
                <Alert severity="success">
                  {t(
                    "create_entity.lookup_no_match",
                    "No existing entity found for this term. Choose a prefill option, then review before creating.",
                  )}
                </Alert>
              )}

              {lookupHasSearched && !lookupLoading && !lookupError && lookupResults.length === 0 && (
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <Button
                    type="button"
                    variant="outlined"
                    onClick={handleSimplePrefill}
                    disabled={loading || aiPrefillLoading}
                    fullWidth
                  >
                    {t("create_entity.simple_prefill", "Prefill slug and display name")}
                  </Button>
                  <Button
                    type="button"
                    variant="outlined"
                    onClick={handleAiPrefill}
                    disabled={loading || aiPrefillLoading}
                    fullWidth
                  >
                    {aiPrefillLoading ? (
                      <Stack direction="row" spacing={1} alignItems="center" justifyContent="center">
                        <CircularProgress
                          aria-label={t(
                            "create_entity.ai_prefill_progress",
                            "AI prefill in progress",
                          )}
                          color="inherit"
                          size={18}
                        />
                        <span>{t("create_entity.ai_prefilling", "Filling with AI...")}</span>
                      </Stack>
                    ) : (
                      t("create_entity.ai_prefill", "Fill the form with AI")
                    )}
                  </Button>
                </Stack>
              )}
            </FormSection>

            <FormSection
              title={t("create_entity.identity_title", "Identity")}
              description={t(
                "create_entity.identity_description",
                "Define the canonical identifier and category for this entity. Prefer an international or English term for the slug.",
              )}
            >
              <TextField
                label={t("create_entity.slug", "Slug")}
                value={slug}
                onChange={(e) => {
                  setSlug(
                    slugifyInput(e.target.value, { preserveTrailingSeparator: true }),
                  );
                  clearError("slug");
                }}
                required
                disabled={loading}
                fullWidth
                error={hasFieldError("slug")}
                helperText={
                  getFieldError("slug") ??
                  t(
                    "create_entity.slug_help",
                    "A unique identifier (e.g., person-albert-einstein)"
                  )
                }
              />

              <Autocomplete
                options={categoryOptions}
                getOptionLabel={(option) => option.label}
                value={categoryOptions.find(opt => opt.id === uiCategoryId) || null}
                onChange={(_, newValue) => setUiCategoryId(newValue?.id || null)}
                disabled={loading}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label={t("create_entity.category", "Category")}
                    helperText={t(
                      "create_entity.category_help",
                      "Optional: Select a category to help organize this entity"
                    )}
                  />
                )}
                isOptionEqualToValue={(option, value) => option.id === value.id}
              />
            </FormSection>

            <FormSection
              title={t("create_entity.display_name_title", "Display name")}
              description={t(
                "create_entity.display_name_help",
                "Optional. Set the preferred human-facing name for this entity.",
              )}
            >
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={2}
                alignItems={{ xs: "stretch", sm: "center" }}
              >
                <FormControl sx={{ minWidth: { xs: "100%", sm: 260 } }}>
                  <InputLabel id="display-name-language-label" shrink>
                    {t("create_entity.display_name_language", "Display name language")}
                  </InputLabel>
                  <Select
                    labelId="display-name-language-label"
                    label={t("create_entity.display_name_language", "Display name language")}
                    value={activeDisplayNameLanguage}
                    onChange={(e) => setActiveDisplayNameLanguage(e.target.value)}
                    disabled={loading}
                    displayEmpty
                    renderValue={(value) =>
                      value
                        ? getLanguageLabel(value)
                        : t("entityTerms.lang_international_short", "International")
                    }
                    sx={LANGUAGE_SELECT_SX}
                    MenuProps={LANGUAGE_MENU_PROPS}
                  >
                    {LANGUAGE_OPTIONS.map((option) => (
                      <MenuItem key={`display-${option.code || "international"}`} value={option.code}>
                        {option.code === ""
                          ? t("create_entity.display_name_language_international", "International / No language")
                          : t(`entityTerms.lang_${option.code}`, option.label)}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {filledDisplayNameLanguages.length > 0 && (
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {filledDisplayNameLanguages.map((language) => (
                      <Chip
                        key={`display-${language || "international"}`}
                        color="success"
                        size="small"
                        label={
                          language
                            ? language.toUpperCase()
                            : t("create_entity.display_name_lang_international_short", "INTL")
                        }
                      />
                    ))}
                  </Stack>
                )}
              </Stack>

              <TextField
                label={t("create_entity.display_name", "Display name")}
                value={displayNames[activeDisplayNameLanguage] ?? ""}
                onChange={(e) =>
                  setDisplayNames((current) => ({
                    ...current,
                    [activeDisplayNameLanguage]: e.target.value,
                  }))
                }
                disabled={loading}
                fullWidth
                helperText={t(
                  "create_entity.display_name_help",
                  "Optional. Set the preferred human-facing name for this entity.",
                )}
                placeholder={
                  activeDisplayNameLanguage
                    ? t("create_entity.display_name_placeholder", {
                        language:
                          getLanguageLabel(activeDisplayNameLanguage),
                        defaultValue: "Display name in {{language}}",
                      })
                    : t(
                        "create_entity.display_name_placeholder_international",
                        "International display name",
                      )
                }
              />
            </FormSection>

            <FormSection
              title={t("create_entity.summary_title", "Summary")}
              description={t(
                "create_entity.summary_section_description",
                "Add descriptive text in one or more languages.",
              )}
            >
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={2}
                alignItems={{ xs: "stretch", sm: "center" }}
              >
                <FormControl sx={{ minWidth: { xs: "100%", sm: 220 } }}>
                  <InputLabel id="summary-language-label">
                    {t("create_entity.summary_language", "Summary language")}
                  </InputLabel>
                  <Select
                    labelId="summary-language-label"
                    label={t("create_entity.summary_language", "Summary language")}
                    value={activeSummaryLanguage}
                    onChange={(e) => setActiveSummaryLanguage(e.target.value)}
                    disabled={loading}
                    renderValue={(value) => getLanguageLabel(value)}
                    sx={LANGUAGE_SELECT_SX}
                    MenuProps={LANGUAGE_MENU_PROPS}
                  >
                    {LANGUAGE_OPTIONS.filter((option) => option.code !== "").map((option) => (
                      <MenuItem key={option.code} value={option.code}>
                        {t(`entityTerms.lang_${option.code}`, option.label)}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {filledSummaryLanguages.length > 0 && (
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {filledSummaryLanguages.map((language) => (
                      <Chip key={language} color="success" size="small" label={language.toUpperCase()} />
                    ))}
                  </Stack>
                )}
              </Stack>

              <TextField
                label={t("create_entity.summary", "Summary")}
                value={summaries[activeSummaryLanguage] ?? ""}
                onChange={(e) =>
                  setSummaries((current) => ({
                    ...current,
                    [activeSummaryLanguage]: e.target.value,
                  }))
                }
                disabled={loading}
                fullWidth
                multiline
                rows={4}
                helperText={t(
                  "create_entity.summary_help",
                  "Optional description of this entity",
                )}
                placeholder={t("create_entity.summary_placeholder", {
                  language:
                    getLanguageLabel(activeSummaryLanguage),
                  defaultValue: "Summary in {{language}}",
                })}
              />
            </FormSection>

            <FormSection
              title={t("entityTerms.title", "Alternative Names & Aliases")}
              description={t(
                "entityTerms.description",
                "Add alternative names, synonyms, or translations to help users find this entity.",
              )}
            >

              {aliases.length === 0 ? (
                <Alert severity="info">
                  {t(
                    "create_entity.aliases_empty",
                    "No aliases yet. Add synonyms or translated names if this entity is known by other terms.",
                  )}
                </Alert>
              ) : (
                <Stack spacing={2}>
                  {aliases.map((alias, index) => (
                    <Paper key={alias.id} variant="outlined" sx={{ p: 2 }}>
                      <Stack spacing={2}>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: 2,
                          }}
                        >
                          <Typography variant="subtitle2">
                            {t("create_entity.alias_row", "Alias {{index}}", {
                              index: index + 1,
                              defaultValue: `Alias ${index + 1}`,
                            })}
                          </Typography>
                          <IconButton
                            aria-label={t("common.remove", "Remove")}
                            onClick={() => removeAliasRow(alias.id)}
                            disabled={loading}
                            size="small"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Box>

                        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                          <TextField
                            label={t("entityTerms.term", "Term")}
                            value={alias.term}
                            onChange={(e) => updateAlias(alias.id, { term: e.target.value })}
                            disabled={loading}
                            fullWidth
                          />

                          <FormControl sx={{ minWidth: { xs: "100%", md: 220 } }}>
                            <InputLabel id={`alias-language-label-${alias.id}`} shrink>
                              {t("entityTerms.language", "Language")}
                            </InputLabel>
                            <Select
                              labelId={`alias-language-label-${alias.id}`}
                              label={t("entityTerms.language", "Language")}
                              value={alias.language}
                              onChange={(e) =>
                                updateAlias(alias.id, { language: e.target.value })
                              }
                              displayEmpty
                              renderValue={(value) =>
                                value
                                  ? getLanguageLabel(value)
                                  : t("entityTerms.lang_international_short", "International")
                              }
                              disabled={loading}
                              sx={LANGUAGE_SELECT_SX}
                              MenuProps={LANGUAGE_MENU_PROPS}
                            >
                              {LANGUAGE_OPTIONS.map((option) => (
                                <MenuItem key={option.code || "international"} value={option.code}>
                                  {option.code
                                    ? t(`entityTerms.lang_${option.code}`, option.label)
                                    : t("entityTerms.lang_international_short", "International")}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>

                          <FormControl sx={{ minWidth: { xs: "100%", md: 180 } }}>
                            <InputLabel id={`alias-kind-label-${alias.id}`}>
                              {t("entityTerms.termKind", "Term kind")}
                            </InputLabel>
                            <Select
                              labelId={`alias-kind-label-${alias.id}`}
                              label={t("entityTerms.termKind", "Term kind")}
                              value={alias.term_kind}
                              onChange={(e) =>
                                updateAlias(alias.id, {
                                  term_kind: e.target.value as AliasDraft["term_kind"],
                                })
                              }
                              disabled={loading}
                            >
                              <MenuItem value="alias">
                                {t("entityTerms.kind_alias", "Alias")}
                              </MenuItem>
                              <MenuItem value="abbreviation">
                                {t("entityTerms.kind_abbreviation", "Abbreviation")}
                              </MenuItem>
                              <MenuItem value="brand">
                                {t("entityTerms.kind_brand", "Brand")}
                              </MenuItem>
                            </Select>
                          </FormControl>
                        </Stack>
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              )}

              <Box>
                <Button variant="outlined" onClick={addAliasRow} disabled={loading}>
                  {t("entityTerms.addTerm", "Add term")}
                </Button>
              </Box>
            </FormSection>

            <FormSection
              title={t("create_entity.actions_title", "Actions")}
              description={t(
                "create_entity.actions_description",
                "Review the information above, then create the entity or cancel.",
              )}
            >
              <Box sx={{ display: "flex", gap: 2 }}>
                <Button
                  variant="outlined"
                  onClick={() => navigate("/entities")}
                  disabled={loading}
                  fullWidth
                >
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={loading}
                  fullWidth
                >
                  {loading
                    ? t("create_entity.creating", "Creating...")
                    : t("create_entity.create", "Create Entity")}
                </Button>
              </Box>
            </FormSection>
          </Stack>
        </form>
      </Stack>
    </Paper>
  );
}

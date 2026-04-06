import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
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
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DeleteIcon from "@mui/icons-material/Delete";

import { createEntity, EntityWrite, getEntityFilterOptions, EntityFilterOptions } from "../api/entities";
import { bulkUpdateEntityTerms, type EntityTermWrite } from "../api/entityTerms";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { useValidationMessage } from "../hooks/useValidationMessage";
import { useNotification } from "../notifications/NotificationContext";
import { slugifyInput } from "../utils/slug";

type ValidationField = "slug";
type AliasDraft = {
  id: string;
  term: string;
  language: string;
};
type SummaryMap = Record<string, string>;

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
];

function createAliasDraft(): AliasDraft {
  return {
    id: globalThis.crypto?.randomUUID?.() ?? `alias-${Date.now()}-${Math.random()}`,
    term: "",
    language: "",
  };
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
      navigate(`/entities/${created.id}`);
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
              title={t("create_entity.identity_title", "Identity")}
              description={t(
                "create_entity.identity_description",
                "Define the canonical identifier and category for this entity.",
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
                  <InputLabel id="display-name-language-label">
                    {t("create_entity.display_name_language", "Display name language")}
                  </InputLabel>
                  <Select
                    labelId="display-name-language-label"
                    label={t("create_entity.display_name_language", "Display name language")}
                    value={activeDisplayNameLanguage}
                    onChange={(e) => setActiveDisplayNameLanguage(e.target.value)}
                    disabled={loading}
                    sx={{
                      "& .MuiSelect-select": {
                        whiteSpace: "normal",
                        overflow: "visible",
                        textOverflow: "clip",
                      },
                    }}
                    MenuProps={{
                      PaperProps: {
                        sx: {
                          "& .MuiMenuItem-root": {
                            whiteSpace: "normal",
                          },
                        },
                      },
                    }}
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
                        defaultValue: `Display name in ${LANGUAGE_OPTIONS.find((option) => option.code === activeDisplayNameLanguage)?.label ?? activeDisplayNameLanguage.toUpperCase()}`,
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
                  defaultValue: `Summary in ${LANGUAGE_OPTIONS.find((option) => option.code === activeSummaryLanguage)?.label ?? activeSummaryLanguage.toUpperCase()}`,
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
                            <InputLabel id={`alias-language-label-${alias.id}`}>
                              {t("entityTerms.language", "Language")}
                            </InputLabel>
                            <Select
                              labelId={`alias-language-label-${alias.id}`}
                              label={t("entityTerms.language", "Language")}
                              value={alias.language}
                              onChange={(e) =>
                                updateAlias(alias.id, { language: e.target.value })
                              }
                              disabled={loading}
                              sx={{
                                "& .MuiSelect-select": {
                                  whiteSpace: "normal",
                                  overflow: "visible",
                                  textOverflow: "clip",
                                },
                              }}
                              MenuProps={{
                                PaperProps: {
                                  sx: {
                                    "& .MuiMenuItem-root": {
                                      whiteSpace: "normal",
                                    },
                                  },
                                },
                              }}
                            >
                              {LANGUAGE_OPTIONS.map((option) => (
                                <MenuItem key={option.code || "international"} value={option.code}>
                                  {t(
                                    `entityTerms.lang_${option.code || "international"}`,
                                    option.label,
                                  )}
                                </MenuItem>
                              ))}
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

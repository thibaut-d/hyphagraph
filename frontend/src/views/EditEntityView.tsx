import { useState, useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
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
  CircularProgress,
  Autocomplete,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { getEntity, updateEntity, EntityWrite, getEntityFilterOptions, EntityFilterOptions } from "../api/entities";
import { EntityRead } from "../types/entity";
import { EntityTermsManager } from "../components/EntityTermsManager";
import { useNotification } from "../notifications/NotificationContext";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { entityPath } from "../utils/entityPath";
import { slugifyInput } from "../utils/slug";

type SummaryMap = Record<string, string>;

const LANGUAGE_OPTIONS = [
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

export function EditEntityView() {
  const { id } = useParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const { showError } = useNotification();
  const navigate = useNavigate();
  const currentLanguage = i18n.language || "en";
  const userLanguage = normalizeUiLanguage(currentLanguage);

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [slug, setSlug] = useState("");
  const [summaries, setSummaries] = useState<SummaryMap>({});
  const [activeSummaryLanguage, setActiveSummaryLanguage] = useState(
    userLanguage === "fr" ? "fr" : "en",
  );
  const [uiCategoryId, setUiCategoryId] = useState<string | null>(null);
  const [filterOptions, setFilterOptions] = useState<EntityFilterOptions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { isRunning: saving, run: runSave } = useAsyncAction(setError);

  // Fetch UI category options
  useEffect(() => {
    getEntityFilterOptions()
      .then(setFilterOptions)
      .catch((err) => {
        const message = t(
          "edit_entity.filter_options_error",
          "Failed to load entity category options"
        );
        setError(message);
        showError(err);
      });
  }, [showError, t]);

  // Extract category options with current language labels
  const categoryOptions = useMemo(() => {
    if (!filterOptions) return [];

    return filterOptions.ui_categories.map(cat => ({
      id: cat.id,
      label: cat.label[currentLanguage] || cat.label.en || cat.id
    }));
  }, [filterOptions, currentLanguage]);

  const getLanguageLabel = (language: string): string => {
    const option = LANGUAGE_OPTIONS.find((candidate) => candidate.code === language);
    return option ? t(`entityTerms.lang_${option.code}`, option.label) : language.toUpperCase();
  };

  useEffect(() => {
    if (!id) return;

    getEntity(id)
      .then((data) => {
        setEntity(data);
        setSlug(data.slug);
        setSummaries(data.summary ?? {});
        setActiveSummaryLanguage(
          data.summary?.[userLanguage] !== undefined
            ? userLanguage
            : Object.keys(data.summary ?? {})[0] ?? userLanguage,
        );
        setUiCategoryId(data.ui_category_id || null);
      })
      .catch((err) => {
        showError(err);
      })
      .finally(() => setLoading(false));
  }, [id, showError, userLanguage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const normalizedSlug = slugifyInput(slug);
    if (!normalizedSlug) {
      setError(t("create_entity.slug_required", "Slug is required"));
      return;
    }
    const SLUG_PATTERN = /^[a-z][a-z0-9-]*$/;
    if (
      normalizedSlug.length < 3 ||
      normalizedSlug.length > 100 ||
      !SLUG_PATTERN.test(normalizedSlug)
    ) {
      setError(t("create_entity.slug_format", "Slug must be 3-100 lowercase letters, digits, or hyphens, starting with a letter"));
      return;
    }

    if (!entity) return;

    const result = await runSave(async () => {
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

      const updatedEntity = await updateEntity(entity.id, payload);

      // Navigate back to the entity detail page
      navigate(entityPath(updatedEntity));
    }, t("common.error", "An error occurred"));

    if (!result.ok) {
      return;
    }
  };

  const filledSummaryLanguages = Object.entries(summaries)
    .filter(([, value]) => value.trim().length > 0)
    .map(([language]) => language);

  if (loading) {
    return (
      <Stack alignItems="center" mt={4}>
        <CircularProgress />
      </Stack>
    );
  }

  if (!entity) {
    return (
      <Typography color="error">
        {t("common.not_found", "Not found")}
      </Typography>
    );
  }

  return (
    <Paper sx={{ p: 4, maxWidth: 900, mx: "auto" }}>
      <Stack spacing={3}>
        {/* Header with back button */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <IconButton onClick={() => navigate(entityPath(entity))} size="small">
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {t("edit_entity.title", "Edit Entity")}
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary">
          {t(
            "edit_entity.description",
            "Update the entity information. The slug is the unique identifier for this entity."
          )}
        </Typography>

        {/* Error message */}
        {error && <Alert severity="error">{error}</Alert>}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
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
                  setError(null);
                }}
                required
                disabled={saving}
                fullWidth
                helperText={t(
                  "create_entity.slug_help",
                  "A unique identifier (e.g., person-albert-einstein)"
                )}
              />

              <Autocomplete
                options={categoryOptions}
                getOptionLabel={(option) => option.label}
                value={categoryOptions.find(opt => opt.id === uiCategoryId) || null}
                onChange={(_, newValue) => setUiCategoryId(newValue?.id || null)}
                disabled={saving}
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
                  <InputLabel id="edit-summary-language-label">
                    {t("create_entity.summary_language", "Summary language")}
                  </InputLabel>
                  <Select
                    labelId="edit-summary-language-label"
                    label={t("create_entity.summary_language", "Summary language")}
                    value={activeSummaryLanguage}
                    onChange={(e) => setActiveSummaryLanguage(e.target.value)}
                    disabled={saving}
                    renderValue={(value) => getLanguageLabel(value)}
                    sx={LANGUAGE_SELECT_SX}
                    MenuProps={LANGUAGE_MENU_PROPS}
                  >
                    {LANGUAGE_OPTIONS.map((option) => (
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
                disabled={saving}
                fullWidth
                multiline
                rows={4}
                helperText={t(
                  "create_entity.summary_help",
                  "Optional description of this entity",
                )}
                placeholder={t("create_entity.summary_placeholder", {
                  language: getLanguageLabel(activeSummaryLanguage),
                  defaultValue: "Summary in {{language}}",
                })}
              />
            </FormSection>

            {/* Entity Terms Manager */}
            {entity && (
              <FormSection
                title={t("edit_entity.terms_title", "Names and terms")}
                description={t(
                  "edit_entity.terms_description",
                  "Manage display names, aliases, abbreviations, and brands for this entity.",
                )}
              >
                <EntityTermsManager entityId={entity.id} readonly={saving} showHeader={false} />
              </FormSection>
            )}

            <FormSection
              title={t("create_entity.actions_title", "Actions")}
              description={t(
                "edit_entity.actions_description",
                "Review the information above, then save your changes or cancel.",
              )}
            >
              <Box sx={{ display: "flex", gap: 2 }}>
                <Button
                  variant="outlined"
                  onClick={() => navigate(entityPath(entity))}
                  disabled={saving}
                  fullWidth
                >
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={saving}
                  fullWidth
                >
                  {saving
                    ? t("edit_entity.saving", "Saving...")
                    : t("edit_entity.save", "Save Changes")}
                </Button>
              </Box>
            </FormSection>
          </Stack>
        </form>
      </Stack>
    </Paper>
  );
}

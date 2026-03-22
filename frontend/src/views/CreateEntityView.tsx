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
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { createEntity, EntityWrite, getEntityFilterOptions, EntityFilterOptions } from "../api/entities";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { useValidationMessage } from "../hooks/useValidationMessage";
import { useNotification } from "../notifications/NotificationContext";

type ValidationField = "slug";

export function CreateEntityView() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { showError } = useNotification();

  const [slug, setSlug] = useState("");
  const [summaryEn, setSummaryEn] = useState("");
  const [summaryFr, setSummaryFr] = useState("");
  const [uiCategoryId, setUiCategoryId] = useState<string | null>(null);
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

    const currentLanguage = i18n.language || 'en';

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
    if (!slug.trim()) {
      setValidationMessage(t("create_entity.slug_required", "Slug is required"), "slug");
      return;
    }
    const SLUG_PATTERN = /^[a-z][a-z0-9-]*$/;
    if (slug.trim().length < 3 || slug.trim().length > 100 || !SLUG_PATTERN.test(slug.trim())) {
      setValidationMessage(t("create_entity.slug_format", "Slug must be 3–100 lowercase letters, digits, or hyphens, starting with a letter"), "slug");
      return;
    }

    const result = await run(async () => {
      const summary: Record<string, string> = {};
      if (summaryEn.trim()) summary.en = summaryEn.trim();
      if (summaryFr.trim()) summary.fr = summaryFr.trim();

      const payload: EntityWrite = {
        slug: slug.trim(),
        summary: Object.keys(summary).length > 0 ? summary : undefined,
        ui_category_id: uiCategoryId || undefined,
      };

      const created = await createEntity(payload);

      // Navigate to the created entity
      navigate(`/entities/${created.id}`);
    }, t("common.error", "An error occurred"));

    if (!result.ok) {
      return;
    }
  };

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
            <TextField
              label={t("create_entity.slug", "Slug")}
              value={slug}
              onChange={(e) => {
                setSlug(e.target.value);
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

            <TextField
              label={t("create_entity.summary_en", "Summary (English)")}
              value={summaryEn}
              onChange={(e) => setSummaryEn(e.target.value)}
              disabled={loading}
              fullWidth
              multiline
              rows={3}
              helperText={t(
                "create_entity.summary_help",
                "Optional description of this entity"
              )}
            />

            <TextField
              label={t("create_entity.summary_fr", "Summary (French)")}
              value={summaryFr}
              onChange={(e) => setSummaryFr(e.target.value)}
              disabled={loading}
              fullWidth
              multiline
              rows={3}
            />

            <Box sx={{ display: "flex", gap: 2, pt: 2 }}>
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
          </Stack>
        </form>
      </Stack>
    </Paper>
  );
}

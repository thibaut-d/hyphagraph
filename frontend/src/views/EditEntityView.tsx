import { useState, useEffect } from "react";
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
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { getEntity, updateEntity, EntityWrite } from "../api/entities";
import { EntityRead } from "../types/entity";
import { EntityTermsManager } from "../components/EntityTermsManager";

export function EditEntityView() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [slug, setSlug] = useState("");
  const [summaryEn, setSummaryEn] = useState("");
  const [summaryFr, setSummaryFr] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!id) return;

    getEntity(id)
      .then((data) => {
        setEntity(data);
        setSlug(data.slug);
        setSummaryEn(data.summary?.en || "");
        setSummaryFr(data.summary?.fr || "");
      })
      .catch((err) => {
        setError(err.message || t("common.error", "An error occurred"));
      })
      .finally(() => setLoading(false));
  }, [id, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!slug.trim()) {
      setError(t("create_entity.slug_required", "Slug is required"));
      return;
    }

    if (!id) return;

    setSaving(true);

    try {
      const summary: Record<string, string> = {};
      if (summaryEn.trim()) summary.en = summaryEn.trim();
      if (summaryFr.trim()) summary.fr = summaryFr.trim();

      const payload: EntityWrite = {
        slug: slug.trim(),
        summary: Object.keys(summary).length > 0 ? summary : undefined,
      };

      await updateEntity(id, payload);

      // Navigate back to the entity detail page
      navigate(`/entities/${id}`);
    } catch (e: any) {
      setError(e.message || t("edit_entity.error", "Failed to update entity"));
      setSaving(false);
    }
  };

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
          <IconButton onClick={() => navigate(`/entities/${id}`)} size="small">
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
            <TextField
              label={t("create_entity.slug", "Slug")}
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              required
              disabled={saving}
              fullWidth
              helperText={t(
                "create_entity.slug_help",
                "A unique identifier (e.g., person-albert-einstein)"
              )}
            />

            <TextField
              label={t("create_entity.summary_en", "Summary (English)")}
              value={summaryEn}
              onChange={(e) => setSummaryEn(e.target.value)}
              disabled={saving}
              fullWidth
              multiline
              rows={4}
              helperText={t(
                "create_entity.summary_help",
                "Optional description of this entity"
              )}
            />

            <TextField
              label={t("create_entity.summary_fr", "Summary (French)")}
              value={summaryFr}
              onChange={(e) => setSummaryFr(e.target.value)}
              disabled={saving}
              fullWidth
              multiline
              rows={4}
            />

            {/* Entity Terms Manager */}
            {id && <EntityTermsManager entityId={id} readonly={saving} />}

            <Box sx={{ display: "flex", gap: 2, pt: 2 }}>
              <Button
                variant="outlined"
                onClick={() => navigate(`/entities/${id}`)}
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
          </Stack>
        </form>
      </Stack>
    </Paper>
  );
}

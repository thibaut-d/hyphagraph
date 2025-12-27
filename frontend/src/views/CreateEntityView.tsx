import { useState } from "react";
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
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { createEntity, EntityWrite } from "../api/entities";

export function CreateEntityView() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const [slug, setSlug] = useState("");
  const [summaryEn, setSummaryEn] = useState("");
  const [summaryFr, setSummaryFr] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!slug.trim()) {
      setError(t("create_entity.slug_required", "Slug is required"));
      return;
    }

    setLoading(true);

    try {
      const summary: Record<string, string> = {};
      if (summaryEn.trim()) summary.en = summaryEn.trim();
      if (summaryFr.trim()) summary.fr = summaryFr.trim();

      const payload: EntityWrite = {
        slug: slug.trim(),
        summary: Object.keys(summary).length > 0 ? summary : undefined,
      };

      const created = await createEntity(payload);

      // Navigate to the created entity
      navigate(`/entities/${created.id}`);
    } catch (e: any) {
      setError(e.message || t("create_entity.error", "Failed to create entity"));
      setLoading(false);
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
        {error && <Alert severity="error">{error}</Alert>}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
            <TextField
              label={t("create_entity.slug", "Slug")}
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              required
              disabled={loading}
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

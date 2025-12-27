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
  MenuItem,
  Grid,
  CircularProgress,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { getSource, updateSource, SourceWrite } from "../api/sources";
import { SourceRead } from "../types/source";

const SOURCE_KINDS = [
  "article",
  "book",
  "website",
  "report",
  "video",
  "podcast",
  "dataset",
  "other",
];

export function EditSourceView() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [source, setSource] = useState<SourceRead | null>(null);
  const [kind, setKind] = useState("article");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [authors, setAuthors] = useState("");
  const [year, setYear] = useState("");
  const [origin, setOrigin] = useState("");
  const [trustLevel, setTrustLevel] = useState("0.5");
  const [summaryEn, setSummaryEn] = useState("");
  const [summaryFr, setSummaryFr] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!id) return;

    getSource(id)
      .then((data) => {
        setSource(data);
        setKind(data.kind || "article");
        setTitle(data.title || "");
        setUrl(data.url || "");
        setAuthors(data.authors?.join(", ") || "");
        setYear(data.year?.toString() || "");
        setOrigin(data.origin || "");
        setTrustLevel(data.trust_level?.toString() || "0.5");
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

    if (!title.trim()) {
      setError(t("create_source.title_required", "Title is required"));
      return;
    }

    if (!url.trim()) {
      setError(t("create_source.url_required", "URL is required"));
      return;
    }

    if (!id) return;

    setSaving(true);

    try {
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
      };

      await updateSource(id, payload);

      // Navigate back to the source detail page
      navigate(`/sources/${id}`);
    } catch (e: any) {
      setError(e.message || t("edit_source.error", "Failed to update source"));
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

  if (!source) {
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
          <IconButton onClick={() => navigate(`/sources/${id}`)} size="small">
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {t("edit_source.title", "Edit Source")}
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary">
          {t(
            "edit_source.description",
            "Update the source information. Sources provide the foundation for relations and claims."
          )}
        </Typography>

        {/* Error message */}
        {error && <Alert severity="error">{error}</Alert>}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  select
                  label={t("create_source.kind", "Kind")}
                  value={kind}
                  onChange={(e) => setKind(e.target.value)}
                  required
                  disabled={saving}
                  fullWidth
                >
                  {SOURCE_KINDS.map((k) => (
                    <MenuItem key={k} value={k}>
                      {t(`create_source.kind_${k}`, k)}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label={t("create_source.year", "Year")}
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  disabled={saving}
                  fullWidth
                  type="number"
                  helperText={t("create_source.year_help", "Publication year")}
                />
              </Grid>
            </Grid>

            <TextField
              label={t("create_source.title_label", "Title")}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              disabled={saving}
              fullWidth
            />

            <TextField
              label={t("create_source.url_label", "URL")}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              disabled={saving}
              fullWidth
              type="url"
              helperText={t(
                "create_source.url_help",
                "Link to the source document or webpage"
              )}
            />

            <TextField
              label={t("create_source.authors", "Authors")}
              value={authors}
              onChange={(e) => setAuthors(e.target.value)}
              disabled={saving}
              fullWidth
              helperText={t(
                "create_source.authors_help",
                "Comma-separated list of authors"
              )}
            />

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label={t("create_source.origin", "Origin")}
                  value={origin}
                  onChange={(e) => setOrigin(e.target.value)}
                  disabled={saving}
                  fullWidth
                  helperText={t(
                    "create_source.origin_help",
                    "Publisher, journal, or platform"
                  )}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label={t("create_source.trust_level", "Trust Level")}
                  value={trustLevel}
                  onChange={(e) => setTrustLevel(e.target.value)}
                  disabled={saving}
                  fullWidth
                  type="number"
                  inputProps={{ min: 0, max: 1, step: 0.1 }}
                  helperText={t(
                    "create_source.trust_level_help",
                    "0 to 1 (0.5 = neutral)"
                  )}
                />
              </Grid>
            </Grid>

            <TextField
              label={t("create_source.summary_en", "Summary (English)")}
              value={summaryEn}
              onChange={(e) => setSummaryEn(e.target.value)}
              disabled={saving}
              fullWidth
              multiline
              rows={3}
              helperText={t(
                "create_source.summary_help",
                "Optional brief description"
              )}
            />

            <TextField
              label={t("create_source.summary_fr", "Summary (French)")}
              value={summaryFr}
              onChange={(e) => setSummaryFr(e.target.value)}
              disabled={saving}
              fullWidth
              multiline
              rows={3}
            />

            <Box sx={{ display: "flex", gap: 2, pt: 2 }}>
              <Button
                variant="outlined"
                onClick={() => navigate(`/sources/${id}`)}
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
                  ? t("edit_source.saving", "Saving...")
                  : t("edit_source.save", "Save Changes")}
              </Button>
            </Box>
          </Stack>
        </form>
      </Stack>
    </Paper>
  );
}

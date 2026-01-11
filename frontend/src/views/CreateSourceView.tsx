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
  MenuItem,
  Grid,
  CircularProgress,
  Chip,
  Collapse,
  Link,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import LinkIcon from "@mui/icons-material/Link";
import EditIcon from "@mui/icons-material/Edit";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";

import { createSource, SourceWrite, extractMetadataFromUrl } from "../api/sources";
import { invalidateSourceFilterCache } from "../utils/cacheUtils";

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

/**
 * Get quality badge for trust level (OCEBM/GRADE standard)
 */
function _getQualityBadge(value: number): {
  label: string;
  color: "success" | "info" | "warning" | "error";
  description: string;
} {
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

export function CreateSourceView() {
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
  const [sourceMetadata, setSourceMetadata] = useState<Record<string, any> | null>(null);

  // UI state
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [autofilled, setAutofilled] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleExtractMetadata = async () => {
    if (!url.trim()) {
      setExtractError(t("create_source.url_required", "URL is required"));
      return;
    }

    setExtractError(null);
    setExtracting(true);
    setAutofilled(false);

    try {
      const metadata = await extractMetadataFromUrl(url.trim());

      // Autofill form with extracted metadata
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
    } catch (e: any) {
      setExtractError(
        e.message || t("create_source.extract_error", "Failed to extract metadata from URL")
      );
    } finally {
      setExtracting(false);
    }
  };

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

    setLoading(true);

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
        source_metadata: sourceMetadata || undefined,
      };

      const created = await createSource(payload);

      // Invalidate filter options cache since we added a new source
      invalidateSourceFilterCache();

      // Navigate to the created source
      navigate(`/sources/${created.id}`);
    } catch (e: any) {
      setError(e.message || t("create_source.error", "Failed to create source"));
      setLoading(false);
    }
  };

  const qualityBadge = _getQualityBadge(parseFloat(trustLevel));

  return (
    <Paper sx={{ p: { xs: 2, sm: 3, md: 4 }, maxWidth: 900, mx: "auto" }}>
      <Stack spacing={3}>
        {/* Header */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <IconButton onClick={() => navigate("/sources")} size="small">
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {t("create_source.title", "Create Source")}
          </Typography>
        </Box>

        <Alert severity="info" icon={<AutoFixHighIcon />}>
          {t(
            "create_source.description_autofill",
            "Paste a URL below and click 'Auto-Fill' to automatically extract metadata from PubMed, arXiv, or any webpage."
          )}
        </Alert>

        {/* Error message (form submission) */}
        {error && <Alert severity="error">{error}</Alert>}

        {/* Main Form */}
        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
            {/* URL Field with Auto-Fill */}
            <Box>
              <Box sx={{ display: "flex", gap: 2, mb: 1 }}>
                <TextField
                  fullWidth
                  label={t("create_source.url_label", "Source URL") + " *"}
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                  disabled={loading}
                  type="url"
                  placeholder="https://pubmed.ncbi.nlm.nih.gov/12345678/"
                  helperText={t(
                    "create_source.url_help",
                    "Paste URL and click 'Auto-Fill' to extract metadata automatically"
                  )}
                  sx={{
                    "& .MuiInputBase-root": autofilled
                      ? {
                          bgcolor: "success.50",
                          borderColor: "success.main",
                        }
                      : {},
                  }}
                />
                <Button
                  variant="contained"
                  onClick={handleExtractMetadata}
                  disabled={extracting || !url.trim() || loading}
                  startIcon={extracting ? <CircularProgress size={20} /> : <AutoFixHighIcon />}
                  sx={{ minWidth: 140, height: 56 }}
                >
                  {extracting
                    ? t("create_source.extracting", "Extracting...")
                    : t("create_source.auto_fill", "Auto-Fill")}
                </Button>
              </Box>

              {/* Extraction Status */}
              {autofilled && (
                <Alert severity="success" sx={{ mt: 1 }}>
                  <strong>{t("create_source.autofilled", "✓ Metadata extracted successfully!")}</strong>
                  {" "}
                  {t("create_source.review_below", "Review the fields below and make corrections if needed.")}
                </Alert>
              )}

              {extractError && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  {extractError}
                  {" "}
                  {t("create_source.manual_fallback", "You can fill the form manually.")}
                </Alert>
              )}

              {/* PubMed/DOI Badges */}
              {sourceMetadata?.pmid && (
                <Box sx={{ mt: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
                  <Chip
                    label={`PubMed ID: ${sourceMetadata.pmid}`}
                    size="small"
                    color="primary"
                    variant="outlined"
                    icon={<LinkIcon />}
                  />
                  {sourceMetadata?.doi && (
                    <Chip
                      label={`DOI: ${sourceMetadata.doi}`}
                      size="small"
                      color="primary"
                      variant="outlined"
                      icon={<LinkIcon />}
                    />
                  )}
                </Box>
              )}
            </Box>

            {/* Required Fields Section */}
            <Paper variant="outlined" sx={{ p: 2, bgcolor: "background.default" }}>
              <Stack spacing={2}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                  {t("create_source.required_fields", "Required Fields")}
                </Typography>

                {/* Title */}
                <TextField
                  label={t("create_source.title_label", "Title") + " *"}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  disabled={loading}
                  fullWidth
                  sx={{
                    "& .MuiInputBase-root": autofilled && title
                      ? {
                          bgcolor: "success.50",
                        }
                      : {},
                  }}
                />

                {/* Kind & Year */}
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      select
                      label={t("create_source.kind", "Type")}
                      value={kind}
                      onChange={(e) => setKind(e.target.value)}
                      required
                      disabled={loading}
                      fullWidth
                      sx={{
                        "& .MuiInputBase-root": autofilled && kind !== "article"
                          ? {
                              bgcolor: "success.50",
                            }
                          : {},
                      }}
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
                      label={t("create_source.year", "Publication Year")}
                      value={year}
                      onChange={(e) => setYear(e.target.value)}
                      disabled={loading}
                      fullWidth
                      type="number"
                      placeholder="2024"
                      sx={{
                        "& .MuiInputBase-root": autofilled && year
                          ? {
                              bgcolor: "success.50",
                            }
                          : {},
                      }}
                    />
                  </Grid>
                </Grid>
              </Stack>
            </Paper>

            {/* Optional Metadata Section */}
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Stack spacing={2}>
                <Typography variant="subtitle2" color="text.secondary">
                  {t("create_source.optional_fields", "Additional Information (Optional)")}
                </Typography>

                {/* Authors */}
                <TextField
                  label={t("create_source.authors", "Authors")}
                  value={authors}
                  onChange={(e) => setAuthors(e.target.value)}
                  disabled={loading}
                  fullWidth
                  placeholder="Smith J, Johnson A, Williams B"
                  helperText={t(
                    "create_source.authors_help",
                    "Comma-separated list"
                  )}
                  sx={{
                    "& .MuiInputBase-root": autofilled && authors
                      ? {
                          bgcolor: "success.50",
                        }
                      : {},
                  }}
                />

                {/* Origin (Journal/Publisher) */}
                <TextField
                  label={t("create_source.origin", "Journal / Publisher")}
                  value={origin}
                  onChange={(e) => setOrigin(e.target.value)}
                  disabled={loading}
                  fullWidth
                  placeholder="Nature Medicine, Oxford University Press, etc."
                  sx={{
                    "& .MuiInputBase-root": autofilled && origin
                      ? {
                          bgcolor: "success.50",
                        }
                      : {},
                  }}
                />

                {/* Quality Score with Visual Badge */}
                <Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
                    <TextField
                      label={t("create_source.trust_level", "Quality Score")}
                      value={trustLevel}
                      onChange={(e) => setTrustLevel(e.target.value)}
                      disabled={loading}
                      type="number"
                      inputProps={{ min: 0, max: 1, step: 0.05 }}
                      sx={{
                        flex: 1,
                        "& .MuiInputBase-root": autofilled && parseFloat(trustLevel) !== 0.5
                          ? {
                              bgcolor: "success.50",
                            }
                          : {},
                      }}
                    />
                    <Chip
                      label={qualityBadge.label}
                      color={qualityBadge.color}
                      sx={{ minWidth: 140 }}
                    />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                    {qualityBadge.description}
                  </Typography>
                  <Link
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      setShowAdvanced(!showAdvanced);
                    }}
                    variant="caption"
                    sx={{ display: "inline-flex", alignItems: "center", gap: 0.5, mt: 0.5 }}
                  >
                    {t("create_source.learn_more", "Learn about quality scoring")}
                    {showAdvanced ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                  </Link>
                  <Collapse in={showAdvanced}>
                    <Alert severity="info" sx={{ mt: 1, fontSize: "0.875rem" }}>
                      <Typography variant="caption" component="div">
                        <strong>Quality scoring is based on Oxford CEBM and GRADE standards:</strong>
                      </Typography>
                      <Typography variant="caption" component="div" sx={{ mt: 1 }}>
                        • 0.90-1.0: Systematic Reviews, Meta-analyses (GRADE ⊕⊕⊕⊕)
                        <br />
                        • 0.75-0.89: RCTs, Cohort Studies (GRADE ⊕⊕⊕⊕/⊕⊕⊕◯)
                        <br />
                        • 0.65-0.74: Case-Control Studies (GRADE ⊕⊕⊕◯)
                        <br />
                        • 0.50-0.64: Case Series, Observational (GRADE ⊕⊕◯◯)
                        <br />
                        • 0.30-0.49: Case Reports, Expert Opinion (GRADE ⊕◯◯◯)
                        <br />• &lt;0.30: Anecdotal evidence
                      </Typography>
                    </Alert>
                  </Collapse>
                </Box>

                {/* Summary (Collapsible) */}
                {(summaryEn || summaryFr || autofilled) && (
                  <>
                    <TextField
                      label={t("create_source.summary_en", "Summary (English)")}
                      value={summaryEn}
                      onChange={(e) => setSummaryEn(e.target.value)}
                      disabled={loading}
                      fullWidth
                      multiline
                      rows={3}
                      placeholder="Brief description or abstract..."
                      sx={{
                        "& .MuiInputBase-root": autofilled && summaryEn
                          ? {
                              bgcolor: "success.50",
                            }
                          : {},
                      }}
                    />

                    <TextField
                      label={t("create_source.summary_fr", "Summary (French)")}
                      value={summaryFr}
                      onChange={(e) => setSummaryFr(e.target.value)}
                      disabled={loading}
                      fullWidth
                      multiline
                      rows={3}
                      placeholder="Résumé ou abstract..."
                    />
                  </>
                )}
              </Stack>
            </Paper>

            {/* Submit Actions */}
            <Box sx={{ display: "flex", gap: 2, pt: 1 }}>
              <Button
                variant="outlined"
                onClick={() => navigate("/sources")}
                disabled={loading}
                fullWidth
              >
                {t("common.cancel", "Cancel")}
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={loading || !title.trim() || !url.trim()}
                fullWidth
                size="large"
              >
                {loading
                  ? t("create_source.creating", "Creating...")
                  : t("create_source.create", "Create Source")}
              </Button>
            </Box>

            {/* Helper Text */}
            <Typography variant="caption" color="text.secondary" sx={{ textAlign: "center", display: "block" }}>
              {t(
                "create_source.next_step_hint",
                "After creating the source, you can extract knowledge and create relations."
              )}
            </Typography>
          </Stack>
        </form>
      </Stack>
    </Paper>
  );
}

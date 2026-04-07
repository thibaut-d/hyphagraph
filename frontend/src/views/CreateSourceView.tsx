import { useNavigate, Link as RouterLink } from "react-router-dom";
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
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import SearchIcon from "@mui/icons-material/Search";

import { useCreateSourceForm } from "../hooks/useCreateSourceForm";
import { useFilterOptionsCache } from "../hooks/useFilterOptionsCache";
import { getSourceFilterOptions, SourceFilterOptions } from "../api/sources";

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

export function CreateSourceView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const filterOptions = useFilterOptionsCache<SourceFilterOptions>(
    'source-filter-options-cache',
    getSourceFilterOptions,
  );

  const {
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
    getFieldError,
    hasFieldError,
    clearError,
    autofilled,
    showAdvanced, setShowAdvanced,
    extracting,
    loading,
    extractError,
    submitError,
    qualityBadge,
    handleExtractMetadata,
    handleSubmit,
  } = useCreateSourceForm();

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

        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <Alert severity="info" icon={<AutoFixHighIcon />} sx={{ flex: 1 }}>
            {t(
              "create_source.description_autofill",
              "Paste a URL below and click 'Auto-Fill' to automatically extract metadata from PubMed, arXiv, or any webpage."
            )}
          </Alert>
          <Button
            component={RouterLink}
            to="/sources/smart-discovery"
            variant="outlined"
            startIcon={<SearchIcon />}
            sx={{ width: { xs: "100%", sm: "auto" }, flexShrink: 0 }}
          >
            {t("create_source.or_smart_discovery", "Or Smart Discovery")}
          </Button>
        </Stack>

        {submitError && <Alert severity="error">{submitError}</Alert>}

        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
            {/* URL Field with Auto-Fill */}
            <Box>
              <Box
                sx={{
                  display: "flex",
                  flexDirection: { xs: "column", sm: "row" },
                  gap: 2,
                  mb: 1,
                }}
              >
                <TextField
                  fullWidth
                  label={t("create_source.url_label", "Source URL") + " *"}
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    clearError("url");
                  }}
                  required
                  disabled={loading}
                  type="url"
                  placeholder={t(
                    "create_source.url_placeholder",
                    "https://pubmed.ncbi.nlm.nih.gov/12345678/"
                  )}
                  error={hasFieldError("url")}
                  helperText={
                    getFieldError("url") ??
                    t(
                      "create_source.url_help",
                      "Paste URL and click 'Auto-Fill' to extract metadata automatically"
                    )
                  }
                  sx={{
                    "& .MuiInputBase-root": autofilled
                      ? { bgcolor: "success.50", borderColor: "success.main" }
                      : {},
                  }}
                />
                <Button
                  variant="contained"
                  onClick={handleExtractMetadata}
                  disabled={extracting || !url.trim() || loading}
                  startIcon={extracting ? <CircularProgress size={20} /> : <AutoFixHighIcon />}
                  sx={{ minWidth: { sm: 140 }, width: { xs: "100%", sm: "auto" }, flexShrink: 0 }}
                >
                  {extracting
                    ? t("create_source.extracting", "Extracting...")
                    : t("create_source.auto_fill", "Auto-Fill")}
                </Button>
              </Box>

              {autofilled && (
                <Alert severity="success" sx={{ mt: 1 }}>
                  <strong>{t("create_source.autofilled")}</strong>
                  {" "}
                  {t("create_source.review_below")}
                </Alert>
              )}

              {extractError && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  {extractError}
                  {" "}
                  {t("create_source.manual_fallback", "You can fill the form manually.")}
                </Alert>
              )}

              {sourceMetadata?.pmid && (
                <Box sx={{ mt: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
                  <Chip
                    label={t("create_source.pubmed_id_chip", { id: sourceMetadata.pmid })}
                    size="small"
                    color="primary"
                    variant="outlined"
                    icon={<LinkIcon />}
                  />
                  {sourceMetadata?.doi && (
                    <Chip
                      label={t("create_source.doi_chip", { id: sourceMetadata.doi })}
                      size="small"
                      color="primary"
                      variant="outlined"
                      icon={<LinkIcon />}
                    />
                  )}
                </Box>
              )}
            </Box>

            {/* Required Fields */}
            <Paper variant="outlined" sx={{ p: 2, bgcolor: "background.default" }}>
              <Stack spacing={2}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                  {t("create_source.required_fields", "Required Fields")}
                </Typography>

                <TextField
                  label={t("create_source.title_label", "Title") + " *"}
                  value={title}
                  onChange={(e) => {
                    setTitle(e.target.value);
                    clearError("title");
                  }}
                  required
                  disabled={loading}
                  fullWidth
                  error={hasFieldError("title")}
                  helperText={getFieldError("title") ?? " "}
                  sx={{
                    "& .MuiInputBase-root": autofilled && title ? { bgcolor: "success.50" } : {},
                  }}
                />

                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 6 }}>
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
                          ? { bgcolor: "success.50" }
                          : {},
                      }}
                    >
                      {(filterOptions?.kinds ?? SOURCE_KINDS).map((k) => (
                        <MenuItem key={k} value={k}>
                          {t(`create_source.kind_${k}`, k)}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <TextField
                      label={t("create_source.year", "Publication Year")}
                      value={year}
                      onChange={(e) => setYear(e.target.value)}
                      disabled={loading}
                      fullWidth
                      type="number"
                      placeholder={t("create_source.year_placeholder", "2024")}
                      sx={{
                        "& .MuiInputBase-root": autofilled && year ? { bgcolor: "success.50" } : {},
                      }}
                    />
                  </Grid>
                </Grid>
              </Stack>
            </Paper>

            {/* Optional Metadata */}
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Stack spacing={2}>
                <Typography variant="subtitle2" color="text.secondary">
                  {t("create_source.optional_fields", "Additional Information (Optional)")}
                </Typography>

                <TextField
                  label={t("create_source.authors", "Authors")}
                  value={authors}
                  onChange={(e) => setAuthors(e.target.value)}
                  disabled={loading}
                  fullWidth
                  placeholder={t(
                    "create_source.authors_placeholder",
                    "Smith J, Johnson A, Williams B"
                  )}
                  helperText={t("create_source.authors_help", "Comma-separated list")}
                  sx={{
                    "& .MuiInputBase-root": autofilled && authors ? { bgcolor: "success.50" } : {},
                  }}
                />

                <TextField
                  label={t("create_source.origin", "Journal / Publisher")}
                  value={origin}
                  onChange={(e) => setOrigin(e.target.value)}
                  disabled={loading}
                  fullWidth
                  placeholder={t(
                    "create_source.origin_placeholder",
                    "Nature Medicine, Oxford University Press, etc."
                  )}
                  sx={{
                    "& .MuiInputBase-root": autofilled && origin ? { bgcolor: "success.50" } : {},
                  }}
                />

                {/* Quality Score */}
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
                          ? { bgcolor: "success.50" }
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
                        <strong>{t("create_source.quality_scoring_header")}</strong>
                      </Typography>
                      <Typography variant="caption" component="div" sx={{ mt: 1 }}>
                        {t("create_source.quality_level_1")}
                        <br />
                        {t("create_source.quality_level_2")}
                        <br />
                        {t("create_source.quality_level_3")}
                        <br />
                        {t("create_source.quality_level_4")}
                        <br />
                        {t("create_source.quality_level_5")}
                        <br />
                        {t("create_source.quality_level_6")}
                      </Typography>
                    </Alert>
                  </Collapse>
                </Box>

                <TextField
                  label={t("create_source.summary_en", "Summary (English)")}
                  value={summaryEn}
                  onChange={(e) => setSummaryEn(e.target.value)}
                  disabled={loading}
                  fullWidth
                  multiline
                  rows={3}
                  placeholder={t("create_source.summary_en_placeholder")}
                  sx={{
                    "& .MuiInputBase-root": autofilled && summaryEn ? { bgcolor: "success.50" } : {},
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
                  placeholder={t("create_source.summary_fr_placeholder")}
                />
              </Stack>
            </Paper>

            {/* Submit */}
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

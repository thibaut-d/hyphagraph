/**
 * Three-stage entity bulk import view.
 *
 * Stage 1 — Upload:  user picks a CSV or JSON file and clicks "Preview"
 * Stage 2 — Preview: per-row table showing new / duplicate / invalid status
 * Stage 3 — Done:    summary of created / skipped / failed counts
 */
import { useRef, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import {
  type EntityImportPreviewRow,
  type ImportPreviewResult,
  type ImportResult,
  executeEntityImport,
  previewEntityImport,
} from "../api/import";

type Stage = "upload" | "preview" | "done";
type FormatType = "csv" | "json";

const STATUS_COLOR: Record<EntityImportPreviewRow["status"], "success" | "warning" | "error"> = {
  new: "success",
  duplicate: "warning",
  invalid: "error",
};

export function ImportEntitiesView() {
  const { t } = useTranslation();

  const [stage, setStage] = useState<Stage>("upload");
  const [format, setFormat] = useState<FormatType>("csv");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResult | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    setError(null);
  }

  async function handlePreview() {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError(t("import.fileTooLarge", "File must be under 10 MB"));
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await previewEntityImport(file, format);
      setPreview(data);
      setStage("preview");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleConfirm() {
    if (!file) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await executeEntityImport(file, format);
      setResult(data);
      setStage("done");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setIsLoading(false);
    }
  }

  function handleReset() {
    setStage("upload");
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  // -------------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------------

  function renderUpload() {
    return (
      <Paper sx={{ p: 3, maxWidth: 600 }}>
        <Typography variant="h6" gutterBottom>
          {t("import.upload_title")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {t("import.upload_description")}
        </Typography>

        <Stack spacing={3}>
          <Box>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
              {t("import.format_label")}
            </Typography>
            <ToggleButtonGroup
              value={format}
              exclusive
              size="small"
              onChange={(_e, val) => { if (val) setFormat(val as FormatType); }}
            >
              <ToggleButton value="csv">CSV</ToggleButton>
              <ToggleButton value="json">JSON</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          <Box>
            <input
              ref={fileInputRef}
              type="file"
              accept={format === "csv" ? ".csv,text/csv" : ".json,application/json"}
              aria-hidden="true"
              tabIndex={-1}
              style={{ position: "absolute", width: 1, height: 1, opacity: 0, overflow: "hidden" }}
              onChange={handleFileChange}
            />
            <Button
              variant="outlined"
              startIcon={<UploadFileIcon />}
              onClick={() => fileInputRef.current?.click()}
            >
              {file ? file.name : t("import.choose_file")}
            </Button>
          </Box>

          {format === "csv" && (
            <Alert severity="info" sx={{ fontSize: "0.8rem" }}>
              {t("import.csv_hint", "CSV must have a header row with columns:")}
              <Box component="code" sx={{ display: "block", mt: 0.5, mb: 0.5, fontSize: "0.75rem", wordBreak: "break-all" }}>
                slug,ui_category_slug,display_name,display_name_en,display_name_fr,summary_en,summary_fr,aliases
              </Box>
              {t("import.csv_example_label", "Example row:")}
              <Box component="code" sx={{ display: "block", mt: 0.5, fontSize: "0.75rem", wordBreak: "break-all" }}>
                aspirin,drugs,,Aspirin,Aspirine,Pain reliever,Analgésique,ASA:en;AAS:fr
              </Box>
              <Box sx={{ mt: 0.5, fontSize: "0.75rem", color: "text.secondary" }}>
                {t("import.csv_aliases_hint", 'aliases: semicolon-separated "term:lang" pairs — e.g. ASA:en;AAS:fr;aspirin:')}
              </Box>
            </Alert>
          )}

          {format === "json" && (
            <Alert severity="info" sx={{ fontSize: "0.8rem" }}>
              {t("import.json_hint")}
              <Box component="code" sx={{ display: "block", mt: 0.5, fontSize: "0.75rem", whiteSpace: "pre-wrap" }}>
                {`[{"slug":"aspirin","ui_category_slug":"drugs","display_name_en":"Aspirin","display_name_fr":"Aspirine","summary_en":"Pain reliever","aliases":"ASA:en;AAS:fr"}]`}
              </Box>
            </Alert>
          )}

          {error && <Alert severity="error">{error}</Alert>}

          <Button
            variant="contained"
            disabled={!file || isLoading}
            onClick={handlePreview}
            startIcon={isLoading ? <CircularProgress size={16} /> : undefined}
          >
            {t("import.preview_button")}
          </Button>
        </Stack>
      </Paper>
    );
  }

  function renderPreview() {
    if (!preview) return null;

    const hasNew = preview.new_count > 0;

    return (
      <Box>
        {/* Summary chips */}
        <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
          <Chip
            label={t("import.stat_new", { count: preview.new_count })}
            color="success"
            variant={preview.new_count > 0 ? "filled" : "outlined"}
            size="small"
          />
          <Chip
            label={t("import.stat_duplicate", { count: preview.duplicate_count })}
            color="warning"
            variant={preview.duplicate_count > 0 ? "filled" : "outlined"}
            size="small"
          />
          <Chip
            label={t("import.stat_invalid", { count: preview.invalid_count })}
            color="error"
            variant={preview.invalid_count > 0 ? "filled" : "outlined"}
            size="small"
          />
        </Stack>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {/* Per-row table */}
        <Paper sx={{ mb: 2, overflow: "auto", maxHeight: 400 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 60 }}>{t("import.col_row")}</TableCell>
                <TableCell>{t("import.col_slug")}</TableCell>
                <TableCell>{t("import.col_display_name", "Display Name")}</TableCell>
                <TableCell>{t("import.col_category", "Category")}</TableCell>
                <TableCell>{t("import.col_summary_en", "Summary (EN)")}</TableCell>
                <TableCell>{t("import.col_status")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {preview.rows.map((row) => (
                <TableRow key={row.row}>
                  <TableCell>{row.row}</TableCell>
                  <TableCell>{row.slug}</TableCell>
                  <TableCell sx={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {row.display_name ?? "—"}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {row.ui_category_slug ?? "—"}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {row.summary_en ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={row.error ?? t(`import.row_status_${row.status}`)}
                      color={STATUS_COLOR[row.status]}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>

        {/* Actions */}
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" onClick={handleReset} disabled={isLoading}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="contained"
            disabled={!hasNew || isLoading}
            onClick={handleConfirm}
            startIcon={isLoading ? <CircularProgress size={16} /> : undefined}
          >
            {t("import.confirm_button", { count: preview.new_count })}
          </Button>
        </Stack>
      </Box>
    );
  }

  function renderDone() {
    if (!result) return null;
    return (
      <Paper sx={{ p: 3, maxWidth: 480 }}>
        <Stack spacing={2} alignItems="flex-start">
          <Stack direction="row" spacing={1} alignItems="center">
            <CheckCircleOutlineIcon color="success" />
            <Typography variant="h6">{t("import.done_title")}</Typography>
          </Stack>

          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Chip label={t("import.stat_created", { count: result.created })} color="success" size="small" />
            <Chip label={t("import.stat_skipped", { count: result.skipped_duplicates })} color="warning" variant="outlined" size="small" />
            {result.failed > 0 && (
              <Chip label={t("import.stat_failed", { count: result.failed })} color="error" size="small" />
            )}
          </Stack>

          <Stack direction="row" spacing={2}>
            <Button variant="outlined" onClick={handleReset}>
              {t("import.import_more")}
            </Button>
            <Button
              variant="contained"
              component={RouterLink}
              to="/entities"
              startIcon={<ArrowBackIcon />}
            >
              {t("import.back_to_entities")}
            </Button>
          </Stack>
        </Stack>
      </Paper>
    );
  }

  // -------------------------------------------------------------------------
  // Layout
  // -------------------------------------------------------------------------

  const stepLabels = [
    t("import.step_upload"),
    t("import.step_preview"),
    t("import.step_done"),
  ];
  const stepIndex = stage === "upload" ? 0 : stage === "preview" ? 1 : 2;

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <Button
          component={RouterLink}
          to="/entities"
          size="small"
          startIcon={<ArrowBackIcon />}
          sx={{ minWidth: 0 }}
        >
          {t("entities.title")}
        </Button>
      </Stack>

      <Typography variant="h5" sx={{ mb: 3 }}>
        {t("import.page_title")}
      </Typography>

      {/* Step indicator */}
      <Stack direction="row" spacing={1} sx={{ mb: 4 }}>
        {stepLabels.map((label, i) => (
          <Chip
            key={label}
            label={`${i + 1}. ${label}`}
            color={i === stepIndex ? "primary" : "default"}
            variant={i === stepIndex ? "filled" : "outlined"}
            size="small"
          />
        ))}
      </Stack>

      {/* Stage content */}
      {stage === "upload" && renderUpload()}
      {stage === "preview" && renderPreview()}
      {stage === "done" && renderDone()}
    </Box>
  );
}

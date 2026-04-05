import type { ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import LinkIcon from "@mui/icons-material/Link";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import UploadFileIcon from "@mui/icons-material/UploadFile";

import type { SaveExtractionResult } from "../../types/extraction";

interface SourceExtractionSectionProps {
  hasUrl: boolean;
  hasRelations: boolean;
  relationsCount: number;
  relationsError: string | null;
  isHighQuality: boolean;
  autoExtracting: boolean;
  uploading: boolean;
  urlExtracting: boolean;
  uploadedFileName: string | null;
  saveResult: SaveExtractionResult | null;
  onClearSaveResult: () => void;
  onAutoExtract: () => void;
  onFileUpload: (event: ChangeEvent<HTMLInputElement>) => void;
  onOpenUrlDialog: () => void;
  onClearUploadedFile: () => void;
}

export function SourceExtractionSection({
  hasUrl,
  hasRelations,
  relationsCount,
  relationsError,
  isHighQuality,
  autoExtracting,
  uploading,
  urlExtracting,
  uploadedFileName,
  saveResult,
  onClearSaveResult,
  onAutoExtract,
  onFileUpload,
  onOpenUrlDialog,
  onClearUploadedFile,
}: SourceExtractionSectionProps) {
  const { t } = useTranslation();

  return (
    <Paper id="knowledge-extraction" sx={{ p: 3 }}>
      <Stack spacing={2}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <SmartToyIcon color="primary" />
          <Typography variant="h5">{t("sources.extract_knowledge", "Knowledge Extraction")}</Typography>
        </Box>

        <Typography variant="body2" color="text.secondary">
          {t(
            "sources.extraction_positioning",
            "Choose one next step for this source: reuse the existing URL, upload a document, or provide another URL for extraction. Review the evidence section above before materializing anything new."
          )}
        </Typography>

        {!hasRelations && !relationsError && (
          <Alert severity="info" icon={<AutoFixHighIcon />}>
            {hasUrl ? (
              <>
                <strong>{t("sources.ready_to_extract", "Ready to extract knowledge!")}</strong>{" "}
                {t(
                  "sources.auto_extract_hint",
                  "Use the source URL below to draft entities and relations for review."
                )}
              </>
            ) : (
              <>
                <strong>{t("sources.no_url", "No URL available")}</strong>{" "}
                {t("sources.upload_hint", "Upload a PDF or TXT file, or add a URL manually, to start extraction.")}
              </>
            )}
          </Alert>
        )}

        {hasRelations && (
          <Alert severity="success">
            {t("sources.has_relations", "This source has {{count}} relations in the knowledge graph.", {
              count: relationsCount,
            })}{" "}
            {t("sources.can_reextract", "You can extract again to add more knowledge.")}
          </Alert>
        )}

        {saveResult && (
          <Alert
            severity={saveResult.skipped_relations.length > 0 ? "warning" : "success"}
            onClose={onClearSaveResult}
          >
            <strong>{t("sources.save_success", "✓ Successfully saved to knowledge graph!")}</strong>
            <br />
            {saveResult.entities_created > 0 && (
              <>
                {t("sources.entities_created", "{{count}} entities created", {
                  count: saveResult.entities_created,
                })}
                <br />
              </>
            )}
            {saveResult.entities_linked > 0 && (
              <>
                {t("sources.entities_linked", "{{count}} entities linked", {
                  count: saveResult.entities_linked,
                })}
                <br />
              </>
            )}
            {saveResult.relations_created > 0 && (
              <>
                {t("sources.relations_created", "{{count}} relations created", {
                  count: saveResult.relations_created,
                })}
                <br />
              </>
            )}
            {saveResult.skipped_relations.length > 0 && (
              <>
                {t(
                  "sources.skipped_relations_warning",
                  "{{count}} staged relations could not be linked and were left pending for review.",
                  { count: saveResult.skipped_relations.length }
                )}
                <br />
                {saveResult.skipped_relations.map((relation) => (
                  <span key={relation.extraction_id}>
                    {relation.relation_type || t("sources.unknown_relation", "Unknown relation")}
                    {relation.text_span ? `: ${relation.text_span}` : ""}
                    <br />
                  </span>
                ))}
              </>
            )}
          </Alert>
        )}


        {hasUrl && (
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t("sources.primary_extraction_action", "Primary action")}
            </Typography>
            <Button
              variant="contained"
              size="large"
              fullWidth
              startIcon={autoExtracting ? <CircularProgress size={20} /> : <AutoFixHighIcon />}
              onClick={onAutoExtract}
              disabled={autoExtracting || uploading || urlExtracting}
              sx={{ py: 2, fontSize: "1.1rem", fontWeight: 600 }}
            >
              {autoExtracting
                ? t("sources.auto_extracting", "Extracting knowledge...")
                : t("sources.auto_extract", "Auto-Extract Knowledge from URL")}
            </Button>
          </Box>
        )}

        <Divider sx={{ my: 1 }}>
          <Typography variant="caption" color="text.secondary">
            {t("sources.or_manual", "Alternative input methods")}
          </Typography>
        </Divider>

        <Typography variant="body2" color="text.secondary">
          {t(
            "sources.alternative_extraction_help",
            "Use these when the stored source URL is missing, incorrect, or not the best text source for extraction."
          )}
        </Typography>

        <Box sx={{ display: "flex", gap: 2, flexDirection: { xs: "column", sm: "row" } }}>
          <input
            accept=".pdf,.txt"
            style={{ display: "none" }}
            id="document-upload"
            type="file"
            onChange={onFileUpload}
            disabled={uploading || autoExtracting}
          />
          <label htmlFor="document-upload" style={{ flex: 1 }}>
            <Button
              variant="outlined"
              component="span"
              fullWidth
              startIcon={uploading ? <CircularProgress size={16} /> : <UploadFileIcon />}
              disabled={uploading || autoExtracting}
            >
              {uploading ? t("sources.uploading", "Uploading...") : t("sources.upload_document", "Upload PDF/TXT")}
            </Button>
          </label>

          <Button
            variant="outlined"
            onClick={onOpenUrlDialog}
            disabled={uploading || urlExtracting || autoExtracting}
            startIcon={<LinkIcon />}
            sx={{ flex: 1 }}
          >
            {t("sources.extract_from_url", "Custom URL")}
          </Button>
        </Box>

        {uploadedFileName && (
          <Chip
            label={t("sources.uploaded_file", "Uploaded: {{name}}", { name: uploadedFileName })}
            onDelete={onClearUploadedFile}
            color="primary"
            variant="outlined"
          />
        )}

      </Stack>
    </Paper>
  );
}

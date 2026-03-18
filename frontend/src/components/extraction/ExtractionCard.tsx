import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { StagedExtractionRead } from "../../api/extractionReview";
import type { ExtractedEntity, ExtractedRelation, ExtractedClaim } from "../../types/extraction";
import {
  Box,
  Button,
  Checkbox,
  Chip,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import WarningIcon from "@mui/icons-material/Warning";

interface ExtractionCardProps {
  extraction: StagedExtractionRead;
  isSelected: boolean;
  onToggleSelect: () => void;
  onApprove: () => void;
  onReject: () => void;
}

function getExtractionTitle(extraction: StagedExtractionRead): string {
  switch (extraction.extraction_type) {
    case "entity": return (extraction.extraction_data as ExtractedEntity).slug;
    case "relation": return (extraction.extraction_data as ExtractedRelation).relation_type;
    case "claim": return (extraction.extraction_data as ExtractedClaim).claim_text;
  }
}

function getStatusColor(status: string): "info" | "success" | "warning" | "error" | "default" {
  switch (status) {
    case "auto_verified": return "info";    // AI-staged, not yet human-reviewed
    case "approved": return "success";       // human approved
    case "pending": return "warning";
    case "rejected": return "error";
    default: return "default";
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case "auto_verified": return <AutoAwesomeIcon fontSize="small" />;
    case "approved": return <CheckCircleIcon fontSize="small" />;
    case "pending": return <WarningIcon fontSize="small" />;
    case "rejected": return <CancelIcon fontSize="small" />;
    default: return undefined;
  }
}

export function ExtractionCard({
  extraction,
  isSelected,
  onToggleSelect,
  onApprove,
  onReject,
}: ExtractionCardProps) {
  const { t } = useTranslation();

  const noNotesLabel = t("extraction_card.no_notes");
  const summary = (() => {
    switch (extraction.extraction_type) {
      case "entity": return (extraction.extraction_data as ExtractedEntity).summary ?? "";
      case "relation": return (extraction.extraction_data as ExtractedRelation).notes || noNotesLabel;
      case "claim": return (extraction.extraction_data as ExtractedClaim).claim_text;
    }
  })();

  const statusLabel: Record<string, string> = {
    auto_verified: t("extraction_card.status_auto_staged"),
    approved: t("extraction_card.status_approved"),
    pending: t("extraction_card.status_pending"),
    rejected: t("extraction_card.status_rejected"),
  };

  return (
    <Paper sx={{ mb: 2 }}>
      <ListItem>
        <Checkbox checked={isSelected} onChange={onToggleSelect} />
        <ListItemText
          primary={
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="h6">{getExtractionTitle(extraction)}</Typography>
              <Chip
                label={extraction.extraction_type}
                size="small"
                color="primary"
                variant="outlined"
              />
              <Chip
                label={statusLabel[extraction.status] ?? extraction.status}
                size="small"
                color={getStatusColor(extraction.status)}
                icon={getStatusIcon(extraction.status)}
              />
              <Chip
                label={t("extraction_card.validation_score", { score: (extraction.validation_score * 100).toFixed(0) })}
                size="small"
                color={extraction.validation_score >= 0.9 ? "success" : "warning"}
              />
              {extraction.validation_flags.length > 0 && (
                <Chip
                  label={`${extraction.validation_flags.length} flags`}
                  size="small"
                  color="warning"
                  icon={<WarningIcon />}
                />
              )}
            </Stack>
          }
          secondary={
            <Stack spacing={1} sx={{ mt: 1 }}>
              <Typography variant="body2">{summary}</Typography>
              {extraction.validation_flags.length > 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t("extraction_card.validation_issues")}
                  </Typography>
                  {extraction.validation_flags.map((flag, idx) => (
                    <Chip key={idx} label={flag} size="small" sx={{ ml: 0.5, mt: 0.5 }} />
                  ))}
                </Box>
              )}
              <Typography variant="caption" color="text.secondary">
                {t("extraction_card.text_span")} &quot;{(extraction.extraction_data as ExtractedEntity).text_span}&quot;
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <Button
                  size="small"
                  variant="contained"
                  color="success"
                  startIcon={<CheckCircleIcon />}
                  onClick={onApprove}
                >
                  {t("extraction_card.approve")}
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  color="error"
                  startIcon={<CancelIcon />}
                  onClick={onReject}
                >
                  {t("extraction_card.reject")}
                </Button>
                {extraction.materialized_entity_id && (
                  <Button
                    size="small"
                    component={RouterLink}
                    to={`/entities/${extraction.materialized_entity_id}`}
                  >
                    {t("extraction_card.view_entity")}
                  </Button>
                )}
              </Stack>
            </Stack>
          }
        />
      </ListItem>
    </Paper>
  );
}

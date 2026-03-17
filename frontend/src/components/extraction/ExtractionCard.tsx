import { Link as RouterLink } from "react-router-dom";
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
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import WarningIcon from "@mui/icons-material/Warning";
import VerifiedIcon from "@mui/icons-material/Verified";

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

function getExtractionSummary(extraction: StagedExtractionRead): string {
  switch (extraction.extraction_type) {
    case "entity": return (extraction.extraction_data as ExtractedEntity).summary ?? "";
    case "relation": return (extraction.extraction_data as ExtractedRelation).notes || "No notes";
    case "claim": return (extraction.extraction_data as ExtractedClaim).claim_text;
  }
}

function getStatusColor(status: string): "success" | "warning" | "error" | "default" {
  switch (status) {
    case "auto_verified":
    case "approved": return "success";
    case "pending": return "warning";
    case "rejected": return "error";
    default: return "default";
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case "auto_verified": return <VerifiedIcon fontSize="small" />;
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
                label={extraction.status}
                size="small"
                color={getStatusColor(extraction.status)}
                icon={getStatusIcon(extraction.status)}
              />
              <Chip
                label={`Score: ${(extraction.validation_score * 100).toFixed(0)}%`}
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
              <Typography variant="body2">{getExtractionSummary(extraction)}</Typography>
              {extraction.validation_flags.length > 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Validation issues:
                  </Typography>
                  {extraction.validation_flags.map((flag, idx) => (
                    <Chip key={idx} label={flag} size="small" sx={{ ml: 0.5, mt: 0.5 }} />
                  ))}
                </Box>
              )}
              <Typography variant="caption" color="text.secondary">
                Text span: &quot;{(extraction.extraction_data as ExtractedEntity).text_span}&quot;
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <Button
                  size="small"
                  variant="contained"
                  color="success"
                  startIcon={<CheckCircleIcon />}
                  onClick={onApprove}
                >
                  Approve
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  color="error"
                  startIcon={<CancelIcon />}
                  onClick={onReject}
                >
                  Reject
                </Button>
                {extraction.materialized_entity_id && (
                  <Button
                    size="small"
                    component={RouterLink}
                    to={`/entities/${extraction.materialized_entity_id}`}
                  >
                    View Entity
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

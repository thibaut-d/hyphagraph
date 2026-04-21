import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Chip,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

interface SourceVerificationSummaryProps {
  title: string;
  trustLevel?: number | null;
  relationsCount: number;
  statementsCount: number;
  isConfirmed: boolean;
}

export function SourceVerificationSummary({
  title,
  trustLevel,
  relationsCount,
  statementsCount,
  isConfirmed,
}: SourceVerificationSummaryProps) {
  const { t } = useTranslation();
  const qualityLabel = trustLevel == null
    ? t("common.not_available", "N/A")
    : `${Math.round(trustLevel * 100)}%`;

  return (
    <Paper variant="outlined" sx={{ p: 2, bgcolor: "background.default" }}>
      <Stack spacing={1.5}>
        <Typography variant="subtitle2">
          {t("sources.verification_summary", "Verification summary")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t(
            "sources.verification_summary_description",
            "{{title}} currently contributes {{relationsCount}} linked relation(s) and {{statementsCount}} recorded statement excerpt(s). Start with the evidence below before running or reviewing extraction actions.",
            {
              title,
              relationsCount,
              statementsCount,
            },
          )}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          <Chip
            label={`${t("sources.relations", "Relations")}: ${relationsCount}`}
            size="small"
            variant="outlined"
            sx={{ maxWidth: "100%" }}
          />
          <Chip
            label={`${t("sources.recorded_statements", "Recorded statements")}: ${statementsCount}`}
            size="small"
            variant="outlined"
            sx={{ maxWidth: "100%" }}
          />
          <Chip
            label={`${t("sources.quality", "Quality")}: ${qualityLabel}`}
            size="small"
            color={trustLevel != null && trustLevel >= 0.75 ? "info" : "default"}
            sx={{ maxWidth: "100%" }}
          />
          <Chip
            label={`${t("relation.status", "Status")}: ${isConfirmed ? t("common.confirmed", "Confirmed") : t("common.draft", "Draft")}`}
            size="small"
            color={isConfirmed ? "success" : "warning"}
            sx={{ maxWidth: "100%" }}
          />
        </Box>
        {relationsCount === 0 && statementsCount === 0 && (
          <Alert severity="info">
            {t(
              "sources.verification_summary_empty",
              "This source does not yet expose any linked evidence in the graph. Use extraction only after reviewing whether a document summary or statement excerpt should be captured."
            )}
          </Alert>
        )}
      </Stack>
    </Paper>
  );
}

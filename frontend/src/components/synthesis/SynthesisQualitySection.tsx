import { useTranslation } from "react-i18next";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import InfoIcon from "@mui/icons-material/Info";
import WarningIcon from "@mui/icons-material/Warning";

interface SynthesisQualitySectionProps {
  confidenceCount: number;
  highConfidenceCount: number;
  lowConfidenceCount: number;
  contradictionCount: number;
}

export function SynthesisQualitySection({
  confidenceCount,
  highConfidenceCount,
  lowConfidenceCount,
  contradictionCount,
}: SynthesisQualitySectionProps) {
  const { t } = useTranslation();

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {t("synthesis.quality.title", "Evidence Quality Overview")}
        </Typography>
        <Stack spacing={2}>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <Chip
              icon={<CheckCircleIcon />}
              label={t("synthesis.quality.high", "High Confidence: {{count}}", { count: highConfidenceCount })}
              color="success"
            />
            <Chip
              icon={<InfoIcon />}
              label={t("synthesis.quality.total", "Total: {{count}}", { count: confidenceCount })}
              variant="outlined"
            />
            {lowConfidenceCount > 0 && (
              <Chip
                icon={<WarningIcon />}
                label={t("synthesis.quality.low", "Low Confidence: {{count}}", { count: lowConfidenceCount })}
                color="warning"
              />
            )}
            {contradictionCount > 0 && (
              <Chip
                icon={<ErrorIcon />}
                label={t("synthesis.quality.contradictions", "Contradictions: {{count}}", { count: contradictionCount })}
                color="error"
              />
            )}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

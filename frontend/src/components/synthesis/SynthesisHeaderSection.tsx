import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Box,
  Breadcrumbs,
  Button,
  Chip,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";

interface SynthesisHeaderSectionProps {
  entityId: string;
  entityLabel: string;
  onBack: () => void;
}

export function SynthesisHeaderSection({
  entityId,
  entityLabel,
  onBack,
}: SynthesisHeaderSectionProps) {
  const { t } = useTranslation();

  return (
    <>
      <Breadcrumbs>
        <Link component={RouterLink} to="/entities" underline="hover">
          {t("menu.entities", "Entities")}
        </Link>
        <Link component={RouterLink} to={`/entities/${entityId}`} underline="hover">
          {entityLabel}
        </Link>
        <Typography color="text.primary">
          {t("synthesis.title", "Synthesis")}
        </Typography>
      </Breadcrumbs>

      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={onBack}
          variant="outlined"
          size="small"
        >
          {t("common.back", "Back to entity")}
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" component="h1">
              {t("synthesis.header", "Evidence Synthesis")}
            </Typography>
            <Chip
              icon={<AutoGraphIcon />}
              label={t("synthesis.algorithmically_derived", "Algorithmically derived")}
              size="small"
              color="info"
              variant="outlined"
            />
          </Stack>
          <Typography variant="h6" color="text.secondary">
            {entityLabel}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t(
              "synthesis.description",
              "Computed overview of the evidence linked to this entity, including confidence, disagreement, and source-backed relation quality."
            )}
          </Typography>
        </Stack>
      </Paper>
    </>
  );
}

import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Box,
  Breadcrumbs,
  Button,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

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
          <Typography variant="h4" component="h1">
            {t("synthesis.header", "Knowledge Synthesis")}
          </Typography>
          <Typography variant="h6" color="text.secondary">
            {entityLabel}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t(
              "synthesis.description",
              "Comprehensive view of all computed knowledge about this entity, including consensus levels and evidence quality."
            )}
          </Typography>
        </Stack>
      </Paper>
    </>
  );
}

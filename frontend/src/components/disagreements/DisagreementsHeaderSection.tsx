import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import WarningIcon from "@mui/icons-material/Warning";

interface DisagreementsHeaderSectionProps {
  entityId: string;
  entityLabel: string;
  onBack: () => void;
}

export function DisagreementsHeaderSection({
  entityId,
  entityLabel,
  onBack,
}: DisagreementsHeaderSectionProps) {
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
          {t("disagreements.title", "Disagreements")}
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

      <Paper sx={{ p: 3, borderColor: "error.main", borderWidth: 2, borderStyle: "solid" }}>
        <Stack spacing={2}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <WarningIcon color="error" sx={{ fontSize: 40 }} />
            <Typography variant="h4" component="h1" color="error">
              {t("disagreements.header", "Contradictory Evidence")}
            </Typography>
          </Box>
          <Typography variant="h6" color="text.secondary">
            {entityLabel}
          </Typography>
          <Alert severity="warning">
            <Typography variant="body2">
              {t(
                "disagreements.honesty_principle",
                "⚠️ Scientific Honesty: We never hide contradictions. All conflicting evidence is shown here to enable informed decision-making."
              )}
            </Typography>
          </Alert>
        </Stack>
      </Paper>
    </>
  );
}

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

interface EvidenceHeaderSectionProps {
  entityId: string;
  entityLabel: string;
  roleType?: string;
  relationCount: number;
  onBack: () => void;
}

export function EvidenceHeaderSection({
  entityId,
  entityLabel,
  roleType,
  relationCount,
  onBack,
}: EvidenceHeaderSectionProps) {
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
        {roleType && (
          <Link component={RouterLink} to={`/entities/${entityId}/properties/${roleType}`} underline="hover">
            {roleType}
          </Link>
        )}
        <Typography color="text.primary">{t("evidence.title", "Evidence")}</Typography>
      </Breadcrumbs>

      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={onBack}
          variant="outlined"
          size="small"
        >
          {t("common.back", "Back")}
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h4" component="h1">
            {roleType
              ? t("evidence.header_filtered", "Evidence for {{roleType}}", { roleType })
              : t("evidence.header_all", "All Evidence")}
          </Typography>
          <Typography variant="h6" color="text.secondary">
            {entityLabel}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t(
              "evidence.description",
              "Complete audit trail of all evidence items (hyperedges) involving this entity. Each row represents a relation from a source document."
            )}
          </Typography>
          <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
            <Chip
              label={t("evidence.count", "{{count}} evidence items", {
                count: relationCount,
              })}
              color="primary"
              variant="outlined"
            />
          </Box>
        </Stack>
      </Paper>
    </>
  );
}

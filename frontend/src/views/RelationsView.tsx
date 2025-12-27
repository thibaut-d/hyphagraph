import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import {
  Typography,
  Paper,
  Stack,
  Button,
  Box,
  Alert,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import SourceIcon from "@mui/icons-material/Source";

export default function RelationsView() {
  const { t } = useTranslation();

  return (
    <Stack spacing={3}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h4">{t("relations.title", "Relations")}</Typography>
        <Button
          component={RouterLink}
          to="/relations/new"
          variant="contained"
          startIcon={<AddIcon />}
        >
          {t("relation.create", "Create relation")}
        </Button>
      </Box>

      <Alert severity="info">
        {t(
          "relations.view_by_source",
          "Relations are currently organized by source. To view relations, please visit the Sources page and select a source."
        )}
      </Alert>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2} alignItems="center">
          <SourceIcon sx={{ fontSize: 64, color: "text.secondary" }} />
          <Typography variant="h6" color="text.secondary">
            {t("relations.no_global_list", "No global relations list available")}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
            {t(
              "relations.explanation",
              "Relations in this system are tied to sources. Each relation must come from a specific source, ensuring traceability and trust."
            )}
          </Typography>
          <Button
            component={RouterLink}
            to="/sources"
            variant="outlined"
            startIcon={<SourceIcon />}
            sx={{ mt: 2 }}
          >
            {t("relations.browse_sources", "Browse Sources")}
          </Button>
        </Stack>
      </Paper>
    </Stack>
  );
}

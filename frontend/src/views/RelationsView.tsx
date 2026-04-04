import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import {
  Typography,
  Paper,
  Stack,
  Button,
  Box,
  Divider,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import PlaylistAddIcon from "@mui/icons-material/PlaylistAdd";
import SourceIcon from "@mui/icons-material/Source";
import SearchIcon from "@mui/icons-material/Search";
import { ExportMenu } from "../components/ExportMenu";

export default function RelationsView() {
  const { t } = useTranslation();

  return (
    <Stack spacing={3}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 1 }}>
        <Box>
          <Typography variant="h4">{t("relations.title", "Relations")}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {t(
              "relations.subtitle",
              "Relations record evidence-backed connections between entities. Each relation is tied to a source document."
            )}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <ExportMenu exportType="relations" buttonText={t("export.relations", "Export Relations")} size="small" />
          <Button
            component={RouterLink}
            to="/relations/batch"
            variant="outlined"
            startIcon={<PlaylistAddIcon />}
          >
            {t("batch_relations.button_label")}
          </Button>
          <Button
            component={RouterLink}
            to="/relations/new"
            variant="contained"
            startIcon={<AddIcon />}
          >
            {t("relation.create", "Create relation")}
          </Button>
        </Stack>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={3}>
          <Typography variant="h6">
            {t("relations.browse_heading", "Browse relations by source")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t(
              "relations.browse_explanation",
              "Relations are grounded in sources: every relation must come from a specific document, ensuring traceability. " +
              "To browse and verify existing relations, navigate to a source and inspect its evidence section."
            )}
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <Button
              component={RouterLink}
              to="/sources"
              variant="outlined"
              startIcon={<SourceIcon />}
            >
              {t("relations.browse_sources", "Browse Sources")}
            </Button>
            <Button
              component={RouterLink}
              to="/search?type=relation"
              variant="outlined"
              startIcon={<SearchIcon />}
            >
              {t("relations.search_relations", "Search Relations")}
            </Button>
          </Stack>

          <Divider />

          <Typography variant="h6">
            {t("relations.create_heading", "Create new relations")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t(
              "relations.create_explanation",
              "Use the form to add a single source-grounded relation, or upload a batch file to create multiple relations at once."
            )}
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <Button
              component={RouterLink}
              to="/relations/new"
              variant="outlined"
              startIcon={<AddIcon />}
            >
              {t("relation.create", "Create relation")}
            </Button>
            <Button
              component={RouterLink}
              to="/relations/batch"
              variant="outlined"
              startIcon={<PlaylistAddIcon />}
            >
              {t("batch_relations.button_label")}
            </Button>
          </Stack>
        </Stack>
      </Paper>
    </Stack>
  );
}

import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import {
  Paper,
  Stack,
  Box,
  Button,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import SearchIcon from "@mui/icons-material/Search";
import { EntityRead } from "../../types/entity";
import { EntityTermsDisplay } from "../EntityTermsDisplay";

/**
 * Header section for entity detail view.
 *
 * Displays entity title, summary, alternative names, and action buttons
 * (back, discover sources, edit, delete, create relation).
 */
export interface EntityDetailHeaderProps {
  /** The entity to display */
  entity: EntityRead;
  /** Callback when delete button is clicked */
  onDeleteClick: () => void;
}

export function EntityDetailHeader({
  entity,
  onDeleteClick,
}: EntityDetailHeaderProps) {
  const { t } = useTranslation();

  return (
    <Paper sx={{ p: { xs: 2, sm: 3 } }}>
      <Stack spacing={2}>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            component={RouterLink}
            to="/entities"
            startIcon={<ArrowBackIcon />}
            size="small"
          >
            {t("common.back", "Back")}
          </Button>
        </Box>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", sm: "center" }}
          spacing={2}
        >
          <Box sx={{ flexGrow: 1 }}>
            <Typography
              variant="h4"
              sx={{ fontSize: { xs: "1.75rem", sm: "2.125rem" } }}
            >
              {entity.slug}
            </Typography>
            <Typography variant="subtitle2" color="text.secondary">
              {entity.summary?.en}
            </Typography>

            {/* Alternative Names/Aliases */}
            <Box sx={{ mt: 2 }}>
              <EntityTermsDisplay entityId={entity.id} />
            </Box>
          </Box>

          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1}
            sx={{ width: { xs: "100%", sm: "auto" } }}
          >
            <Button
              component={RouterLink}
              to={`/sources/smart-discovery?entity=${entity.slug}`}
              variant="contained"
              color="secondary"
              startIcon={<SearchIcon />}
              size="small"
              sx={{ width: { xs: "100%", sm: "auto" } }}
            >
              {t("entity.discover_sources", "Discover Sources")}
            </Button>
            <Button
              component={RouterLink}
              to={`/entities/${entity.id}/edit`}
              color="primary"
              startIcon={<EditIcon />}
              size="small"
              sx={{ width: { xs: "100%", sm: "auto" } }}
            >
              {t("common.edit", "Edit")}
            </Button>
            <Button
              onClick={onDeleteClick}
              color="error"
              startIcon={<DeleteIcon />}
              size="small"
              sx={{ width: { xs: "100%", sm: "auto" } }}
            >
              {t("common.delete", "Delete")}
            </Button>
            <Button
              component={RouterLink}
              to={`/relations/new?entity_id=${entity.id}`}
              variant="outlined"
              startIcon={<AddIcon />}
              size="small"
              sx={{ width: { xs: "100%", sm: "auto" } }}
            >
              {t("relation.create", "Create relation")}
            </Button>
          </Stack>
        </Stack>
      </Stack>
    </Paper>
  );
}

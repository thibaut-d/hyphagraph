import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import {
  Paper,
  Stack,
  Box,
  Breadcrumbs,
  Button,
  Chip,
  Link,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import SearchIcon from "@mui/icons-material/Search";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { EntityRead } from "../../types/entity";
import { EntityTermsDisplay } from "../EntityTermsDisplay";
import type { EntityTermRead } from "../../api/entityTerms";
import { entitySubpath } from "../../utils/entityPath";

function normalizeUiLanguage(language: string): string {
  return language.split("-")[0] || "en";
}

function resolveLocalizedText(
  value: Record<string, string> | null | undefined,
  preferredLanguage: string,
): string | null {
  if (!value) return null;
  return (
    value[preferredLanguage] ||
    value[""] ||
    value.en ||
    Object.values(value).find((candidate) => candidate.trim().length > 0) ||
    null
  );
}

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
  const { t, i18n } = useTranslation();
  const [displayName, setDisplayName] = useState<string | null>(null);
  const handleTermsLoaded = useCallback((terms: EntityTermRead[]) => {
    const currentLanguage = normalizeUiLanguage(i18n.language || "en");
    const preferred =
      terms.find((term) => term.is_display_name && term.language === currentLanguage) ||
      terms.find((term) => term.is_display_name && !term.language) ||
      terms.find((term) => term.is_display_name && term.language === "en");
    setDisplayName(preferred?.term ?? null);
  }, [i18n.language]);
  const primaryLabel = displayName || entity.slug;
  const summary = resolveLocalizedText(
    entity.summary,
    normalizeUiLanguage(i18n.language || "en"),
  );

  return (
    <Paper sx={{ p: { xs: 2, sm: 3 } }}>
      <Stack spacing={2}>
        <Breadcrumbs>
          <Link component={RouterLink} to="/entities" underline="hover" color="inherit">
            {t("menu.entities", "Entities")}
          </Link>
          <Typography color="text.primary">{primaryLabel}</Typography>
        </Breadcrumbs>

        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", sm: "center" }}
          spacing={2}
        >
          <Box sx={{ flexGrow: 1 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
              <Typography
                variant="h4"
                sx={{ fontSize: { xs: "1.75rem", sm: "2.125rem" } }}
              >
                {primaryLabel}
              </Typography>
              {displayName && (
                <Typography variant="body2" color="text.secondary">
                  {entity.slug}
                </Typography>
              )}
              {entity.status === "draft" && (
                <Chip
                  label={t("entity.status_draft", "Draft")}
                  size="small"
                  color="warning"
                  variant="outlined"
                />
              )}
            </Box>
            {summary && (
              <Typography variant="subtitle2" color="text.secondary">
                {summary}
              </Typography>
            )}

            {/* Alternative Names/Aliases */}
            <Box sx={{ mt: 2 }}>
              <EntityTermsDisplay entityId={entity.id} onTermsLoaded={handleTermsLoaded} />
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
              to={entitySubpath(entity, "edit")}
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

        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Button
            component={RouterLink}
            to="/entities"
            startIcon={<ArrowBackIcon />}
            size="small"
          >
            {t("common.back", "Back")}
          </Button>
          <Button
            component={RouterLink}
            to={entitySubpath(entity, "synthesis")}
            startIcon={<AutoGraphIcon />}
            size="small"
            variant="outlined"
          >
            {t("entity.synthesis", "Synthesis")}
          </Button>
          <Button
            component={RouterLink}
            to={entitySubpath(entity, "disagreements")}
            startIcon={<WarningAmberIcon />}
            size="small"
            variant="outlined"
            color="warning"
          >
            {t("entity.disagreements", "Disagreements")}
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}

import { useTranslation } from "react-i18next";
import {
  Paper,
  Stack,
  Box,
  Button,
  Chip,
  Typography,
  Badge,
  Alert,
} from "@mui/material";
import FilterListIcon from "@mui/icons-material/FilterList";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import CloseIcon from "@mui/icons-material/Close";
import { EntityRead } from "../../types/entity";
import { InferenceRead } from "../../types/inference";
import { ScopeFilter } from "../../api/inferences";
import { InferenceBlock } from "../InferenceBlock";

/**
 * Inference section for entity detail view.
 *
 * Displays related assertions (inferences) with filter controls and warnings.
 * Includes evidence filter button, scope filter panel, and inference display.
 */
export interface InferenceSectionProps {
  /** The entity being displayed */
  entity: EntityRead;
  /** The raw inference data (may be null if not loaded) */
  inference: InferenceRead | null;
  /** The filtered inference data (null if no filters active) */
  filteredInference: InferenceRead | null;
  /** Current active scope filters */
  scopeFilter: ScopeFilter;
  /** Number of active evidence filters */
  evidenceFilterCount: number;
  /** Number of relations hidden by evidence filters */
  hiddenRelationsCount: number;
  /** Whether sources are currently loading */
  loadingSources: boolean;
  /** Callback to open evidence filter drawer */
  onOpenEvidenceFilter: () => void;
  /** Callback to clear all scope filters */
  onClearScopeFilters: () => void;
  /** The scope filter panel component */
  scopeFilterPanel: React.ReactNode;
}

export function InferenceSection({
  entity,
  inference,
  filteredInference,
  scopeFilter,
  evidenceFilterCount,
  hiddenRelationsCount,
  loadingSources,
  onOpenEvidenceFilter,
  onClearScopeFilters,
  scopeFilterPanel,
}: InferenceSectionProps) {
  const { t } = useTranslation();

  return (
    <Paper sx={{ p: { xs: 2, sm: 3 } }}>
      <Stack spacing={2}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h5">
              {t("entity.inference", "Related assertions")}
            </Typography>
            <Chip
              icon={<AutoGraphIcon />}
              label={t("inference.computed", "Computed")}
              size="small"
              color="info"
              variant="outlined"
            />
          </Stack>

          <Stack direction="row" spacing={2}>
            {/* Evidence Filter Button */}
            <Badge badgeContent={evidenceFilterCount} color="primary">
              <Button
                variant="outlined"
                startIcon={<FilterListIcon />}
                onClick={onOpenEvidenceFilter}
                disabled={loadingSources}
              >
                {t("filters.evidence", "Filter Evidence")}
              </Button>
            </Badge>

            {Object.keys(scopeFilter).length > 0 && (
              <Button
                size="small"
                onClick={onClearScopeFilters}
                startIcon={<CloseIcon />}
              >
                Clear Scope Filters
              </Button>
            )}
          </Stack>
        </Box>

        {/* Warning when evidence is hidden by filters */}
        {evidenceFilterCount > 0 && hiddenRelationsCount > 0 && (
          <Alert severity="warning">
            {t(
              "filters.evidence_hidden_warning",
              "{{count}} relation(s) hidden by evidence filters. These are excluded from the view but do not affect computed scores.",
              { count: hiddenRelationsCount }
            )}
          </Alert>
        )}

        {/* Scope Filter Controls */}
        {scopeFilterPanel}

        {/* Inference Display */}
        {filteredInference ? (
          <InferenceBlock
            inference={filteredInference}
            currentEntitySlug={entity.slug}
          />
        ) : (
          <Typography color="text.secondary">
            {t("common.no_data", "No data")}
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}

/**
 * SynthesisView
 *
 * Aggregated view of all computed knowledge for an entity.
 * Shows the "big picture" of what we know about an entity
 * across all relations, inferences, and evidence.
 *
 * Purpose (from UX.md):
 * - Aggregate view of entity-level knowledge
 * - Show all inferences grouped by role type
 * - Display consensus levels across properties
 * - Highlight knowledge gaps and contradictions
 * - Provide quick navigation to detailed views
 *
 * Navigation: Entity Detail → View Synthesis → This View
 */

import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ErrorIcon from "@mui/icons-material/Error";
import InfoIcon from "@mui/icons-material/Info";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { SynthesisFooterSection } from "../components/synthesis/SynthesisFooterSection";
import { SynthesisHeaderSection } from "../components/synthesis/SynthesisHeaderSection";
import { SynthesisQualitySection } from "../components/synthesis/SynthesisQualitySection";
import { SynthesisRelationsSection } from "../components/synthesis/SynthesisRelationsSection";
import { SynthesisStatsSection } from "../components/synthesis/SynthesisStatsSection";
import type { RelationRead } from "../types/relation";
import { useEntityInferenceDetail } from "../hooks/useEntityInferenceDetail";
import { entityPath, entitySubpath } from "../utils/entityPath";

/**
 * SynthesisView Component
 *
 * Displays comprehensive synthesis of all knowledge about an entity:
 * - Overview statistics (# of relations, sources, confidence levels)
 * - All inferences grouped by role type
 * - Consensus indicators
 * - Knowledge gaps
 * - Quick links to detailed explanations
 */
export function SynthesisView() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, error, loading } = useEntityInferenceDetail(id, "Failed to load synthesis");
  const entity = data?.entity ?? null;
  const inference = data?.inference ?? null;
  const stats = inference?.stats;
  const relationKindSummaries = inference?.relation_kind_summaries;

  // Loading state
  if (loading) {
    return (
      <Stack alignItems="center" mt={4}>
        <CircularProgress />
        <Typography variant="body2" color="text.secondary" mt={2}>
          {t("synthesis.loading", "Generating synthesis...")}
        </Typography>
      </Stack>
    );
  }

  // Error state — always render back button so tests/users can navigate away
  if (error || !entity) {
    return (
      <Stack spacing={2}>
        <Box>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate(`/entities/${id}`)}
            variant="outlined"
            size="small"
          >
            {t("common.back", "Back")}
          </Button>
        </Box>
        <Alert severity="error">
          {error || t("common.error", "An error occurred")}
        </Alert>
      </Stack>
    );
  }

  const entityLabel = entity.slug;
  const canonicalEntityPath = entityPath(entity);

  // Calculate synthesis statistics
  const relationsByKind = inference?.relations_by_kind || {};
  const relationGroups = Object.values(relationsByKind) as RelationRead[][];
  const totalRelations = stats?.total_relations ?? Object.values(relationsByKind).reduce(
    (sum, relations) => sum + relations.length,
    0
  );

  // Count unique sources
  const uniqueSources = new Set<string>();
  relationGroups.forEach((relations) => {
    relations.forEach(rel => {
      if (rel.source_id) uniqueSources.add(rel.source_id);
    });
  });

  // Calculate confidence metrics
  let totalConfidence = 0;
  let confidenceCount = 0;
  let highConfidenceCount = 0;
  let lowConfidenceCount = 0;
  let contradictionCount = 0;

  relationGroups.forEach((relations) => {
    relations.forEach(rel => {
      if (rel.confidence !== undefined && rel.confidence !== null) {
        totalConfidence += rel.confidence;
        confidenceCount++;
        if (rel.confidence > 0.7) highConfidenceCount++;
        if (rel.confidence < 0.4) lowConfidenceCount++;
      }
      if (rel.direction === "contradicts") contradictionCount++;
    });
  });

  const averageConfidence = stats?.average_confidence ?? (
    confidenceCount > 0 ? totalConfidence / confidenceCount : 0
  );
  const uniqueSourcesCount = stats?.unique_sources_count ?? uniqueSources.size;
  const highConfidenceTotal = stats?.high_confidence_count ?? highConfidenceCount;
  const lowConfidenceTotal = stats?.low_confidence_count ?? lowConfidenceCount;
  const contradictionTotal = stats?.contradiction_count ?? contradictionCount;
  const confidenceTotal = stats?.confidence_count ?? confidenceCount;
  const relationTypeCount = stats?.relation_type_count ?? Object.keys(relationsByKind).length;

  const hasData = totalRelations > 0;

  return (
    <Stack spacing={3}>
      <SynthesisHeaderSection
        entityId={entity.slug}
        entityLabel={entityLabel}
        onBack={() => navigate(canonicalEntityPath)}
      />

      {hasData ? (
        <>
          {/* SYN31-H1: top-level synthesis summary before metrics */}
          <Paper sx={{ p: 3 }}>
            <Stack spacing={2}>
              <Typography variant="h6">
                {t("synthesis.summary.heading", "Current evidence reading")}
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                {averageConfidence >= 0.7 ? (
                  <Chip icon={<CheckCircleIcon />} label={t("synthesis.summary.high_confidence", "High confidence")} color="success" size="small" />
                ) : averageConfidence >= 0.4 ? (
                  <Chip icon={<WarningAmberIcon />} label={t("synthesis.summary.moderate_confidence", "Moderate confidence")} color="warning" size="small" />
                ) : (
                  <Chip icon={<ErrorIcon />} label={t("synthesis.summary.low_confidence", "Low confidence")} color="error" size="small" />
                )}
                {contradictionTotal > 0 && (
                  <Chip icon={<WarningAmberIcon />} label={t("synthesis.summary.contradictions", "Contradictions present")} color="warning" variant="outlined" size="small" />
                )}
              </Stack>
              <Typography variant="body2" color="text.secondary">
                {t(
                  "synthesis.summary.statement",
                  "Evidence from {{sources}} source(s) across {{relations}} relation(s) yields an average confidence of {{confidence}}%." +
                  (contradictionTotal > 0
                    ? " {{contradictions}} contradictory relation(s) introduce meaningful disagreement — see the Disagreements view for details."
                    : " No contradictions detected in current evidence."),
                  {
                    sources: uniqueSourcesCount,
                    relations: totalRelations,
                    confidence: Math.round(averageConfidence * 100),
                    contradictions: contradictionTotal,
                  }
                )}
              </Typography>
              {contradictionTotal > 0 && (
                <>
                  <Divider />
                  <Typography variant="caption" color="text.secondary">
                    {t(
                      "synthesis.summary.uncertainty_note",
                      "Contradictions are preserved, not resolved. Inspect individual disagreements to understand competing evidence before drawing conclusions."
                    )}
                  </Typography>
                </>
              )}
            </Stack>
          </Paper>

          <SynthesisStatsSection
            totalRelations={totalRelations}
            uniqueSourcesCount={uniqueSourcesCount}
            averageConfidence={averageConfidence}
            relationTypeCount={relationTypeCount}
          />

          <SynthesisQualitySection
            confidenceCount={confidenceTotal}
            highConfidenceCount={highConfidenceTotal}
            lowConfidenceCount={lowConfidenceTotal}
            contradictionCount={contradictionTotal}
          />

          <SynthesisRelationsSection
            summaries={relationKindSummaries}
            relationsByKind={relationsByKind}
            onSelectKind={(kind) => navigate(entitySubpath(entity, `properties/${kind}`))}
          />

          <SynthesisFooterSection
            contradictionCount={contradictionTotal}
            relationTypeCount={relationTypeCount}
            onViewDisagreements={() => navigate(entitySubpath(entity, "disagreements"))}
            onBackToDetail={() => navigate(canonicalEntityPath)}
          />
        </>
      ) : (
        <Alert severity="info" icon={<InfoIcon />}>
          <Typography variant="body1" gutterBottom>
            {t("synthesis.no_data.title", "No synthesized knowledge available")}
          </Typography>
          <Typography variant="body2">
            {t("synthesis.no_data.description",
              "This entity has no computed inferences yet. Add relations and sources to generate knowledge synthesis."
            )}
          </Typography>
        </Alert>
      )}
    </Stack>
  );
}

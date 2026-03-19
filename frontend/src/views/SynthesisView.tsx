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
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import InfoIcon from "@mui/icons-material/Info";

import { SynthesisFooterSection } from "../components/synthesis/SynthesisFooterSection";
import { SynthesisHeaderSection } from "../components/synthesis/SynthesisHeaderSection";
import { SynthesisQualitySection } from "../components/synthesis/SynthesisQualitySection";
import { SynthesisRelationsSection } from "../components/synthesis/SynthesisRelationsSection";
import { SynthesisStatsSection } from "../components/synthesis/SynthesisStatsSection";
import type { RelationRead } from "../types/relation";
import { resolveLabel } from "../utils/i18nLabel";
import { useEntityInferenceDetail } from "../hooks/useEntityInferenceDetail";

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
  const { t, i18n } = useTranslation();
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

  // Error state
  if (error || !entity) {
    return (
      <Alert severity="error">
        {error || t("common.error", "An error occurred")}
      </Alert>
    );
  }

  const entityLabel = resolveLabel(entity.slug, entity.summary, i18n.language);

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
        entityId={id!}
        entityLabel={entityLabel}
        onBack={() => navigate(`/entities/${id}`)}
      />

      {hasData ? (
        <>
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
            onSelectKind={(kind) => navigate(`/entities/${id}/properties/${kind}`)}
          />

          <SynthesisFooterSection
            contradictionCount={contradictionTotal}
            relationTypeCount={relationTypeCount}
            onViewDisagreements={() => navigate(`/entities/${id}/disagreements`)}
            onBackToDetail={() => navigate(`/entities/${id}`)}
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

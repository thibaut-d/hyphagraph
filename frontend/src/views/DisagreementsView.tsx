/**
 * DisagreementsView
 *
 * Dedicated view for exploring contradictions and conflicting claims
 * about an entity. Upholds scientific honesty by never hiding contradictions.
 *
 * Purpose (from UX.md & VIBE.md):
 * - Show all contradictory evidence side-by-side
 * - Never hide contradictions (fundamental principle)
 * - Enable scientific audit of conflicting claims
 * - Provide clear source attribution for each side
 * - Help users understand WHY sources disagree
 *
 * Navigation: Entity Detail → View Disagreements → This View
 * Also accessible from: SynthesisView → View Disagreements button
 */

import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";

import { resolveLabel } from "../utils/i18nLabel";
import { useEntityInferenceDetail } from "../hooks/useEntityInferenceDetail";
import type { RelationRead } from "../types/relation";
import { DisagreementsFooterSection } from "../components/disagreements/DisagreementsFooterSection";
import {
  DisagreementGroup,
  DisagreementsGroupsSection,
} from "../components/disagreements/DisagreementsGroupsSection";
import { DisagreementsHeaderSection } from "../components/disagreements/DisagreementsHeaderSection";
import { DisagreementsSummarySection } from "../components/disagreements/DisagreementsSummarySection";

/**
 * DisagreementsView Component
 *
 * Shows contradictions in a structured, scientific manner:
 * - Group contradictions by role type
 * - Side-by-side comparison of supporting vs contradicting evidence
 * - Source attribution for each claim
 * - Confidence metrics
 * - Links to full evidence details
 *
 * Scientific Honesty Principle: ALL contradictions are shown,
 * never hidden or minimized.
 */
export function DisagreementsView() {
  const { id } = useParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { data, error, loading } = useEntityInferenceDetail(id, "Failed to load disagreements");
  const entity = data?.entity ?? null;
  const inference = data?.inference ?? null;

  // Loading state
  if (loading) {
    return (
      <Stack alignItems="center" mt={4}>
        <CircularProgress />
        <Typography variant="body2" color="text.secondary" mt={2}>
          {t("disagreements.loading", "Analyzing contradictions...")}
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

  const entityLabel = resolveLabel(entity.label || entity.slug, entity.summary, i18n.language);

  // Group relations by role type and direction
  const disagreementGroups: DisagreementGroup[] = inference?.disagreement_groups
    ? inference.disagreement_groups
    : [];

  if (disagreementGroups.length === 0 && inference && inference.relations_by_kind) {
    Object.entries(inference.relations_by_kind).forEach(([roleType, relationArray]) => {
      const typedRelations = relationArray as RelationRead[];

      const supporting = typedRelations.filter(rel =>
        rel.direction === "supports" || !rel.direction
      );
      const contradicting = typedRelations.filter(rel =>
        rel.direction === "contradicts"
      );

      // Only include if there are contradictions
      if (contradicting.length > 0) {
        const totalConfidence = typedRelations.reduce(
          (sum, rel) => sum + (rel.confidence || 0),
          0
        ) / typedRelations.length;

        disagreementGroups.push({
          kind: roleType,
          supporting,
          contradicting,
          confidence: totalConfidence,
        });
      }
    });
  }

  const hasDisagreements = disagreementGroups.length > 0;
  const totalContradictions = disagreementGroups.reduce(
    (sum, group) => sum + group.contradicting.length,
    0
  );

  return (
    <Stack spacing={3}>
      <DisagreementsHeaderSection
        entityId={id}
        entityLabel={entityLabel}
        onBack={() => navigate(`/entities/${id}`)}
      />

      {hasDisagreements ? (
        <>
          <DisagreementsSummarySection
            groupCount={disagreementGroups.length}
            contradictionCount={totalContradictions}
          />

          <DisagreementsGroupsSection
            groups={disagreementGroups}
            onViewExplanation={(roleType) => navigate(`/entities/${id}/properties/${roleType}`)}
          />

          <DisagreementsFooterSection
            onViewSynthesis={() => navigate(`/entities/${id}/synthesis`)}
            onBackToDetail={() => navigate(`/entities/${id}`)}
          />
        </>
      ) : (
        <Alert severity="success" icon={<ThumbUpIcon />}>
          <Typography variant="body1" gutterBottom>
            {t("disagreements.no_data.title", "No contradictory evidence is currently surfaced")}
          </Typography>
          <Typography variant="body2">
            {t("disagreements.no_data.description",
              "No conflicting evidence is currently shown for this entity. This may reflect agreement in the available sources, or simply limited coverage in the current evidence base."
            )}
          </Typography>
        </Alert>
      )}
    </Stack>
  );
}

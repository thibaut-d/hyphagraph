/**
 * ExtractedRelationsList component
 *
 * Displays extracted relations and allows user to select which ones to create.
 */
import React from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Checkbox,
  Stack,
  Alert,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  MedicalServices as MedicalServicesIcon,
  Science as ScienceIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import type {
  ExtractedRelation,
  RelationType,
  ConfidenceLevel,
  ExtractedRelationEvidenceContext,
  StatementKind,
  FindingPolarity,
  StudyDesign,
  ExtractedEntity,
} from "../types/extraction";
import {
  getRelationDisplayRoles,
  getRelationKey,
} from "../utils/extractionRelation";
import { getExtractedEntityDisplayLabel } from "../utils/entityDisplay";

interface ExtractedRelationsListProps {
  relations: ExtractedRelation[];
  entities?: ExtractedEntity[];
  selectedRelations: Set<string>;
  onToggle: (relationKey: string) => void;
}

const confidenceColors: Record<ConfidenceLevel, "success" | "warning" | "error"> = {
  high: "success",
  medium: "warning",
  low: "error",
};

const relationTypeLabels: Record<RelationType, string> = {
  treats: "Treats",
  causes: "Causes",
  prevents: "Prevents",
  increases_risk: "Increases Risk",
  decreases_risk: "Decreases Risk",
  mechanism: "Mechanism",
  contraindicated: "Contraindicated",
  interacts_with: "Interacts With",
  metabolized_by: "Metabolized By",
  biomarker_for: "Biomarker For",
  affects_population: "Affects Population",
  measures: "Measures",
  diagnoses: "Diagnoses",
  predicts: "Predicts",
  other: "Other",
};

const relationTypeIcons: Record<RelationType, React.ReactElement> = {
  treats: <MedicalServicesIcon fontSize="small" />,
  causes: <WarningIcon fontSize="small" />,
  prevents: <MedicalServicesIcon fontSize="small" />,
  increases_risk: <TrendingUpIcon fontSize="small" />,
  decreases_risk: <TrendingDownIcon fontSize="small" />,
  mechanism: <ScienceIcon fontSize="small" />,
  contraindicated: <WarningIcon fontSize="small" />,
  interacts_with: <ScienceIcon fontSize="small" />,
  metabolized_by: <ScienceIcon fontSize="small" />,
  biomarker_for: <ScienceIcon fontSize="small" />,
  affects_population: <ScienceIcon fontSize="small" />,
  measures: <ScienceIcon fontSize="small" />,
  diagnoses: <ScienceIcon fontSize="small" />,
  predicts: <ScienceIcon fontSize="small" />,
  other: <ScienceIcon fontSize="small" />,
};

const statementKindLabels: Record<StatementKind, string> = {
  finding: "Finding",
  background: "Background",
  hypothesis: "Hypothesis",
  methodology: "Methodology",
};

const findingPolarityLabels: Record<FindingPolarity, string> = {
  supports: "Supports",
  contradicts: "Contradicts",
  mixed: "Mixed",
  neutral: "Neutral",
  uncertain: "Uncertain",
};

const studyDesignLabels: Record<StudyDesign, string> = {
  meta_analysis: "Meta-analysis",
  systematic_review: "Systematic review",
  randomized_controlled_trial: "Randomized trial",
  nonrandomized_trial: "Non-randomized trial",
  cohort_study: "Cohort study",
  case_control_study: "Case-control study",
  cross_sectional_study: "Cross-sectional study",
  case_series: "Case series",
  case_report: "Case report",
  guideline: "Guideline",
  review: "Review",
  animal_study: "Animal study",
  in_vitro: "In vitro",
  background: "Background",
  unknown: "Unknown design",
};

function humanizeScopeKey(key: string) {
  return key.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderEvidenceContextChips(evidenceContext?: ExtractedRelationEvidenceContext | null) {
  if (!evidenceContext) {
    return null;
  }

  const chips: React.ReactElement[] = [
    <Chip
      key="statement-kind"
      label={statementKindLabels[evidenceContext.statement_kind]}
      size="small"
      variant="outlined"
      color={evidenceContext.statement_kind === "finding" ? "primary" : "default"}
    />,
  ];

  if (evidenceContext.finding_polarity) {
    chips.push(
      <Chip
        key="finding-polarity"
        label={findingPolarityLabels[evidenceContext.finding_polarity]}
        size="small"
        variant="outlined"
        color={
          evidenceContext.finding_polarity === "supports"
            ? "success"
            : evidenceContext.finding_polarity === "contradicts"
              ? "error"
              : "warning"
        }
      />,
    );
  }

  if (evidenceContext.evidence_strength) {
    chips.push(
      <Chip
        key="evidence-strength"
        label={`Evidence: ${evidenceContext.evidence_strength}`}
        size="small"
        variant="outlined"
      />,
    );
  }

  if (evidenceContext.study_design) {
    chips.push(
      <Chip
        key="study-design"
        label={studyDesignLabels[evidenceContext.study_design]}
        size="small"
        variant="outlined"
      />,
    );
  }

  if (evidenceContext.sample_size || evidenceContext.sample_size_text) {
    chips.push(
      <Chip
        key="sample-size"
        label={evidenceContext.sample_size_text || `n=${evidenceContext.sample_size}`}
        size="small"
        variant="outlined"
      />,
    );
  }

  return chips;
}

function renderScopeChips(scope?: ExtractedRelation["scope"]) {
  if (!scope) {
    return null;
  }

  return Object.entries(scope).map(([key, value]) => (
    <Chip
      key={`scope-${key}`}
      label={`${humanizeScopeKey(key)}: ${String(value)}`}
      size="small"
      variant="outlined"
    />
  ));
}

function RelationToken({
  role,
  label,
}: {
  role?: string;
  label: string;
}) {
  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "center",
        maxWidth: "100%",
        minWidth: 0,
        px: 1,
        py: 0.5,
        borderRadius: 1,
        border: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        color: "text.primary",
        gap: 0.5,
      }}
    >
      {role && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ flexShrink: 0, textTransform: "uppercase", letterSpacing: 0.3 }}
        >
          {role}
        </Typography>
      )}
      <Typography
        variant="body2"
        fontWeight={600}
        sx={{ overflowWrap: "anywhere", whiteSpace: "normal" }}
      >
        {label}
      </Typography>
    </Box>
  );
}

export const ExtractedRelationsList: React.FC<ExtractedRelationsListProps> = ({
  relations,
  entities = [],
  selectedRelations,
  onToggle,
}) => {
  const entityLabels = new Map(
    entities.map((entity) => [entity.slug, getExtractedEntityDisplayLabel(entity)] as const),
  );

  if (relations.length === 0) {
    return (
      <Alert severity="info">
        No relations were extracted from the document.
      </Alert>
    );
  }

  return (
    <Stack spacing={2}>
      {relations.map((relation, index) => {
        const relationKey = getRelationKey(relation);
        const isSelected = selectedRelations.has(relationKey);
        const roles = getRelationDisplayRoles(relation).map(({ role, value }) => ({
          role,
          value: entityLabels.get(value) || value,
        }));
        const evidenceContext = relation.evidence_context ?? relation.study_context;
        const evidenceChips = renderEvidenceContextChips(evidenceContext);
        const scopeChips = renderScopeChips(relation.scope);

        return (
          <Card
            key={`${relationKey}-${index}`}
            variant="outlined"
            sx={{
              opacity: isSelected ? 1 : 0.6,
              transition: "opacity 0.2s",
              "&:hover": { opacity: 1 },
            }}
          >
            <CardContent>
              <Stack spacing={2}>
                {/* Relation header with checkbox */}
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: { xs: 1, sm: 2 },
                    flexWrap: { xs: "wrap", sm: "nowrap" },
                  }}
                >
                  <Checkbox
                    checked={isSelected}
                    onChange={() => onToggle(relationKey)}
                    sx={{ mt: -1 }}
                  />

                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    {/* Relation type and hyperedge role set */}
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        flexWrap: "wrap",
                      }}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 0.5,
                          px: 1,
                          py: 0.5,
                          bgcolor: "primary.main",
                          color: "white",
                          borderRadius: 1,
                          maxWidth: "100%",
                        }}
                      >
                        {relationTypeIcons[relation.relation_type]}
                        <Typography variant="body2" fontWeight="medium" sx={{ overflowWrap: "anywhere" }}>
                          {relationTypeLabels[relation.relation_type]}
                        </Typography>
                      </Box>
                    </Box>

                    {((evidenceChips && evidenceChips.length > 0) || (scopeChips && scopeChips.length > 0)) && (
                      <Box sx={{ mt: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
                        {scopeChips}
                        {evidenceChips}
                      </Box>
                    )}

                    <Box sx={{ mt: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
                      {roles.map(({ role, value }) => (
                        <RelationToken
                          key={`${relationKey}-${role}-${value}`}
                          role={role}
                          label={value}
                        />
                      ))}
                    </Box>

                    {/* Notes */}
                    {relation.notes && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mt: 1, fontStyle: "italic" }}
                      >
                        Note: {relation.notes}
                      </Typography>
                    )}

                    {evidenceContext?.assertion_text && (
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          Core statement
                        </Typography>
                        <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
                          {evidenceContext.assertion_text}
                        </Typography>
                      </Box>
                    )}

                    {evidenceContext?.methodology_text && (
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          Evidence / methodology
                        </Typography>
                        <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
                          {evidenceContext.methodology_text}
                        </Typography>
                      </Box>
                    )}

                    {evidenceContext?.statistical_support && (
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          Statistical support
                        </Typography>
                        <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
                          {evidenceContext.statistical_support}
                        </Typography>
                      </Box>
                    )}
                  </Box>

                  {/* Confidence */}
                  <Chip
                    label={relation.confidence}
                    size="small"
                    color={confidenceColors[relation.confidence]}
                    sx={{ ml: { xs: 0, sm: 0 } }}
                  />
                </Box>

                {/* Text span */}
                <Box
                  sx={{
                    p: 1.5,
                    bgcolor: "grey.50",
                    borderRadius: 1,
                    borderLeft: "3px solid",
                    borderColor: "primary.main",
                    ml: { xs: 0, sm: 5 }, // Align with content (after checkbox) on wider screens.
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{ fontStyle: "italic", overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}
                  >
                    "{relation.text_span}"
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
};

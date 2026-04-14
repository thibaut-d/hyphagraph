import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { StagedExtractionRead } from "../../api/extractionReview";
import type { ExtractedEntity, ExtractedRelation, ExtractedClaim } from "../../types/extraction";
import {
  getRelationDisplayRoles,
  getRelationObject,
  getRelationSubject,
} from "../../utils/extractionRelation";
import {
  Box,
  Button,
  Checkbox,
  Chip,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import WarningIcon from "@mui/icons-material/Warning";

interface ExtractionCardProps {
  extraction: StagedExtractionRead;
  isSelected: boolean;
  onToggleSelect: () => void;
  onApprove: () => void;
  onReject: () => void;
}

function isClaimExtraction(extraction: StagedExtractionRead): extraction is StagedExtractionRead & {
  extraction_data: ExtractedClaim;
} {
  return extraction.extraction_type === "claim";
}

function isRelationExtraction(extraction: StagedExtractionRead): extraction is StagedExtractionRead & {
  extraction_data: ExtractedRelation;
} {
  return extraction.extraction_type === "relation";
}

function humanizeToken(value: string | null | undefined): string {
  if (!value || !value.trim()) {
    return "Unknown";
  }

  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (char) => char.toUpperCase());
}

function formatRelationSentence(relation: ExtractedRelation): string {
  const subject = getRelationSubject(relation);
  const object = getRelationObject(relation);

  if (subject !== "Unknown" && object !== "Unknown" && subject !== object) {
    return `${subject} ${humanizeToken(relation.relation_type).toLowerCase()} ${object}`;
  }

  const displayRoles = getRelationDisplayRoles(relation);
  if (displayRoles.length > 0) {
    return displayRoles
      .map(({ role, value }) => `${humanizeToken(role)}: ${value}`)
      .join(" • ");
  }

  return humanizeToken(relation.relation_type);
}

const REQUIRED_RELATION_ROLE_GROUPS: Record<string, string[][]> = {
  treats: [["agent"], ["target"]],
  causes: [["agent"], ["target", "outcome"]],
  prevents: [["agent"], ["target", "outcome"]],
  increases_risk: [["agent", "condition"], ["target", "outcome"]],
  decreases_risk: [["agent", "condition"], ["target", "outcome"]],
  contraindicated: [["agent"], ["target", "condition"]],
  metabolized_by: [["agent"], ["target", "mechanism"]],
  biomarker_for: [["biomarker"], ["target", "condition"]],
  measures: [["measured_by"], ["target", "outcome", "condition"]],
};

const CONTEXTUAL_ENTITY_PREFIXES = [
  "dose-",
  "dosage-",
  "duration-",
  "timeframe-",
  "participants-",
  "participant-count-",
  "sample-size-",
  "study-design-",
];

function getRelationStructuralWarnings(relation: ExtractedRelation, t: (key: string, opts?: Record<string, unknown>) => string): string[] {
  const warnings: string[] = [];
  const roles = relation.roles ?? [];
  const requiredGroups = REQUIRED_RELATION_ROLE_GROUPS[relation.relation_type] ?? [];

  for (const group of requiredGroups) {
    const matchingRoles = roles.filter((role) => group.includes(role.role_type));
    if (matchingRoles.length === 0) {
      warnings.push(
        t("extraction_card.missing_required_roles", {
          roles: group.map((role) => humanizeToken(role)).join(" / "),
        })
      );
      continue;
    }

    const contextualCoreRoles = matchingRoles.filter((role) =>
      CONTEXTUAL_ENTITY_PREFIXES.some((prefix) => (role.entity_slug ?? "").startsWith(prefix))
    );
    if (contextualCoreRoles.length === matchingRoles.length) {
      warnings.push(
        t("extraction_card.invalid_contextual_role", {
          role: group.map((role) => humanizeToken(role)).join(" / "),
          entity: contextualCoreRoles[0]?.entity_slug || "Unknown",
        })
      );
    }
  }

  return warnings;
}

function getExtractionTextSpan(extraction: StagedExtractionRead): string | null {
  const textSpan = extraction.extraction_data.text_span;
  if (typeof textSpan === "string" && textSpan.trim().length > 0) {
    return textSpan;
  }
  return null;
}

function getExtractionTitle(extraction: StagedExtractionRead): string {
  switch (extraction.extraction_type) {
    case "entity": return (extraction.extraction_data as ExtractedEntity).slug;
    case "relation": return formatRelationSentence(extraction.extraction_data as ExtractedRelation);
    case "claim": return (extraction.extraction_data as ExtractedClaim).claim_text;
  }
}

function getStatusColor(status: string): "info" | "success" | "warning" | "error" | "default" {
  switch (status) {
    case "auto_verified": return "info";    // AI-staged, not yet human-reviewed
    case "approved": return "success";       // human approved
    case "pending": return "warning";
    case "rejected": return "error";
    default: return "default";
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case "auto_verified": return <AutoAwesomeIcon fontSize="small" />;
    case "approved": return <CheckCircleIcon fontSize="small" />;
    case "pending": return <WarningIcon fontSize="small" />;
    case "rejected": return <CancelIcon fontSize="small" />;
    default: return undefined;
  }
}

export function ExtractionCard({
  extraction,
  isSelected,
  onToggleSelect,
  onApprove,
  onReject,
}: ExtractionCardProps) {
  const { t } = useTranslation();

  const noNotesLabel = t("extraction_card.no_notes");
  const textSpan = getExtractionTextSpan(extraction);
  const showMissingTextSpanHint =
    extraction.validation_flags.includes("claim_text_span_not_found") ||
    extraction.validation_flags.includes("text_span_not_found");
  const relationData = isRelationExtraction(extraction) ? extraction.extraction_data : null;
  const relationRoles = relationData?.roles ?? [];
  const relationEvidenceContext = relationData?.evidence_context ?? relationData?.study_context;
  const relationStructuralWarnings = relationData
    ? getRelationStructuralWarnings(relationData, t)
    : [];
  const summary = (() => {
    switch (extraction.extraction_type) {
      case "entity": return (extraction.extraction_data as ExtractedEntity).summary ?? "";
      case "relation":
        return relationData?.notes?.trim() || t("extraction_card.relation_summary_help");
      case "claim": return (extraction.extraction_data as ExtractedClaim).claim_text;
    }
  })();

  const statusLabel: Record<string, string> = {
    auto_verified: t("extraction_card.status_auto_staged"),
    approved: t("extraction_card.status_approved"),
    pending: t("extraction_card.status_pending"),
    rejected: t("extraction_card.status_rejected"),
  };

  return (
    <Paper sx={{ mb: 2 }}>
      <ListItem>
        <Checkbox checked={isSelected} onChange={onToggleSelect} />
        <ListItemText
          secondaryTypographyProps={{ component: "div" }}
          primary={
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="h6">{getExtractionTitle(extraction)}</Typography>
              <Chip
                label={extraction.extraction_type}
                size="small"
                color="primary"
                variant="outlined"
              />
              <Chip
                label={statusLabel[extraction.status] ?? extraction.status}
                size="small"
                color={getStatusColor(extraction.status)}
                icon={getStatusIcon(extraction.status)}
              />
              <Chip
                label={t("extraction_card.validation_score", { score: (extraction.validation_score * 100).toFixed(0) })}
                size="small"
                color={extraction.validation_score >= 0.9 ? "success" : "warning"}
              />
              {extraction.validation_flags.length > 0 && (
                <Chip
                  label={`${extraction.validation_flags.length} flags`}
                  size="small"
                  color="warning"
                  icon={<WarningIcon />}
                />
              )}
            </Stack>
          }
          secondary={
            <Stack spacing={1} sx={{ mt: 1 }} component="div">
              <Typography variant="body2" component="span">{summary}</Typography>
              {isRelationExtraction(extraction) && (
                <Stack spacing={1} component="span">
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" component="span">
                    <Chip
                      label={t("extraction_card.relation_type", {
                        relationType: humanizeToken(extraction.extraction_data.relation_type),
                      })}
                      size="small"
                      variant="outlined"
                    />
                    {relationEvidenceContext?.study_design && (
                      <Chip
                        label={t("extraction_card.study_design", {
                          studyDesign: humanizeToken(relationEvidenceContext.study_design),
                        })}
                        size="small"
                        variant="outlined"
                      />
                    )}
                    {relationEvidenceContext?.sample_size_text && (
                      <Chip
                        label={t("extraction_card.sample_size", {
                          sampleSize: relationEvidenceContext.sample_size_text,
                        })}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Stack>
                  {relationRoles.length > 0 ? (
                    <Box component="span">
                      <Typography variant="caption" color="text.secondary" component="span">
                        {t("extraction_card.linked_roles")}
                      </Typography>
                      {relationRoles.map((role) => (
                        <Chip
                          key={`${role.role_type ?? "unknown-role"}-${role.entity_slug ?? "unknown-entity"}`}
                          label={t("extraction_card.role_value", {
                            role: humanizeToken(role.role_type),
                            entity: role.entity_slug || "Unknown",
                          })}
                          size="small"
                          variant="outlined"
                          sx={{ ml: 0.5, mt: 0.5 }}
                        />
                      ))}
                    </Box>
                  ) : (
                    <Typography variant="caption" color="warning.main" component="span">
                      {t("extraction_card.no_structured_roles")}
                    </Typography>
                  )}
                  {relationStructuralWarnings.length > 0 && (
                    <Box component="span">
                      <Typography variant="caption" color="warning.main" component="span">
                        {t("extraction_card.structural_issues")}
                      </Typography>
                      {relationStructuralWarnings.map((warning) => (
                        <Chip
                          key={warning}
                          label={warning}
                          size="small"
                          color="warning"
                          variant="outlined"
                          sx={{ ml: 0.5, mt: 0.5 }}
                        />
                      ))}
                    </Box>
                  )}
                </Stack>
              )}
              {isClaimExtraction(extraction) && (
                <Stack spacing={1} component="span">
                  {extraction.extraction_data.entities_involved.length > 0 && (
                    <Box component="span">
                      <Typography variant="caption" color="text.secondary" component="span">
                        {t("extraction_card.entities_involved")}
                      </Typography>
                      {extraction.extraction_data.entities_involved.map((entity) => (
                        <Chip
                          key={entity}
                          label={entity}
                          size="small"
                          variant="outlined"
                          sx={{ ml: 0.5, mt: 0.5 }}
                        />
                      ))}
                    </Box>
                  )}
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" component="span">
                    <Chip
                      label={t("extraction_card.claim_type", {
                        claimType: extraction.extraction_data.claim_type,
                      })}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      label={t("extraction_card.evidence_strength", {
                        evidenceStrength: extraction.extraction_data.evidence_strength,
                      })}
                      size="small"
                      variant="outlined"
                    />
                  </Stack>
                </Stack>
              )}
              {extraction.validation_flags.length > 0 && (
                <Box component="span">
                  <Typography variant="caption" color="text.secondary" component="span">
                    {t("extraction_card.validation_issues")}
                  </Typography>
                  {extraction.validation_flags.map((flag, idx) => (
                    <Chip key={idx} label={flag} size="small" sx={{ ml: 0.5, mt: 0.5 }} />
                  ))}
                </Box>
              )}
              {textSpan ? (
                <Typography variant="caption" color="text.secondary" component="span">
                  {t("extraction_card.text_span")} &quot;{textSpan}&quot;
                </Typography>
              ) : showMissingTextSpanHint ? (
                <Typography variant="caption" color="warning.main" component="span">
                  {t("extraction_card.no_exact_source_quote")}
                </Typography>
              ) : null}
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
                <Button
                  size="small"
                  variant="contained"
                  color="success"
                  startIcon={<CheckCircleIcon />}
                  onClick={onApprove}
                >
                  {t("extraction_card.approve")}
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  color="error"
                  startIcon={<CancelIcon />}
                  onClick={onReject}
                >
                  {t("extraction_card.reject")}
                </Button>
                {extraction.materialized_entity_id && (
                  <Button
                    size="small"
                    component={RouterLink}
                    to={`/entities/${extraction.materialized_entity_id}`}
                  >
                    {t("extraction_card.view_entity")}
                  </Button>
                )}
                {extraction.materialized_relation_id && (
                  <Button
                    size="small"
                    component={RouterLink}
                    to={`/relations/${extraction.materialized_relation_id}`}
                  >
                    {t("extraction_card.view_relation")}
                  </Button>
                )}
                <Button
                  size="small"
                  component={RouterLink}
                  to={`/sources/${extraction.source_id}`}
                >
                  {t("extraction_card.view_source")}
                </Button>
              </Stack>
            </Stack>
          }
        />
      </ListItem>
    </Paper>
  );
}

import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import type { RelationKindSummaryRead } from "../../types/inference";
import type { RelationRead } from "../../types/relation";
import {
  formatDirectionLabel,
  formatRelationStatement,
  formatRelationContext,
} from "../../utils/relationPresentation";

interface SynthesisRelationsSectionProps {
  summaries?: RelationKindSummaryRead[];
  relationsByKind: Record<string, RelationRead[]>;
  onSelectKind: (kind: string) => void;
}

export function SynthesisRelationsSection({
  summaries,
  relationsByKind,
  onSelectKind,
}: SynthesisRelationsSectionProps) {
  const { t } = useTranslation();
  const displaySummaries =
    summaries ??
    Object.entries(relationsByKind).map(([kind, relations]) => {
      const supportingCount = relations.filter(
        (relation) => relation.direction === "supports",
      ).length;
      const contradictingCount = relations.filter(
        (relation) => relation.direction === "contradicts",
      ).length;
      return {
        kind,
        relation_count: relations.length,
        average_confidence:
          relations.reduce((sum, relation) => sum + (relation.confidence || 0), 0) /
          relations.length,
        supporting_count: supportingCount,
        contradicting_count: contradictingCount,
        neutral_count: relations.length - supportingCount - contradictingCount,
      };
    });

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        {t("synthesis.relations.title", "Relations by Type")}
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        {t(
          "synthesis.relations.description",
          "Each section summarizes one relation type, shows a few representative evidence statements, and then links to the full property detail."
        )}
      </Typography>

      <Stack spacing={1}>
        {displaySummaries.map((summary) => {
          const relationArray = relationsByKind[summary.kind] || [];
          const kindConfidence = summary.average_confidence;
          const examples = relationArray.slice(0, 3);
          const hiddenCount = Math.max(relationArray.length - examples.length, 0);

          return (
            <Accordion key={summary.kind}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 2, width: "100%" }}>
                  <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                    {summary.kind}
                  </Typography>
                  <Chip
                    label={`${summary.relation_count} relation${summary.relation_count !== 1 ? "s" : ""}`}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={t("synthesis.relations.contradictions", {
                      defaultValue: "{{count}} contradiction{{suffix}}",
                      count: summary.contradicting_count,
                      suffix: summary.contradicting_count === 1 ? "" : "s",
                    })}
                    size="small"
                    color={summary.contradicting_count > 0 ? "error" : "default"}
                    variant={summary.contradicting_count > 0 ? "filled" : "outlined"}
                  />
                  <Chip
                    label={`${Math.round(kindConfidence * 100)}% confidence`}
                    size="small"
                    color={kindConfidence > 0.7 ? "success" : kindConfidence > 0.4 ? "warning" : "error"}
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
                  <Chip
                    label={t("synthesis.relations.supporting", {
                      defaultValue: "{{count}} supporting",
                      count: summary.supporting_count,
                    })}
                    size="small"
                    color="success"
                    variant="outlined"
                  />
                  <Chip
                    label={t("synthesis.relations.contradicting", {
                      defaultValue: "{{count}} contradicting",
                      count: summary.contradicting_count,
                    })}
                    size="small"
                    color={summary.contradicting_count > 0 ? "error" : "default"}
                    variant="outlined"
                  />
                  <Chip
                    label={t("synthesis.relations.neutral", {
                      defaultValue: "{{count}} neutral or mixed",
                      count: summary.neutral_count,
                    })}
                    size="small"
                    variant="outlined"
                  />
                </Stack>

                <Typography variant="body2" color="text.secondary" paragraph>
                  {t(
                    "synthesis.relations.examples_description",
                    "Representative evidence statements are shown below. Open the property detail for the full trace, filters, and explanation."
                  )}
                </Typography>

                <List dense>
                  {examples.map((relation) => {
                    const contextParts = formatRelationContext(relation);
                    const secondaryParts = [
                      formatDirectionLabel(relation.direction),
                      relation.confidence != null
                        ? t("synthesis.relation.confidence", {
                            defaultValue: "Confidence: {{value}}%",
                            value: Math.round(relation.confidence * 100),
                          })
                        : null,
                      ...contextParts,
                    ].filter(Boolean);

                    return (
                      <ListItem key={relation.id} disablePadding sx={{ py: 0.5 }}>
                        <ListItemText
                          primary={formatRelationStatement(relation, summary.kind)}
                          secondary={secondaryParts.join(" • ")}
                        />
                      </ListItem>
                    );
                  })}
                </List>

                {hiddenCount > 0 && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
                    {t("synthesis.relations.more_examples", {
                      defaultValue: "{{count}} more evidence item{{suffix}} available in the property detail.",
                      count: hiddenCount,
                      suffix: hiddenCount === 1 ? "" : "s",
                    })}
                  </Typography>
                )}

                <Button variant="outlined" onClick={() => onSelectKind(summary.kind)}>
                  {t("synthesis.relations.open_property", "Open property detail")}
                </Button>
              </AccordionDetails>
            </Accordion>
          );
        })}
      </Stack>
    </Box>
  );
}

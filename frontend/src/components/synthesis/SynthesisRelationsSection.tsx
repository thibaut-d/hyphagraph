import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { RelationKindSummaryRead } from "../../types/inference";

interface SynthesisRelationsSectionProps {
  summaries?: RelationKindSummaryRead[];
  relationsByKind: Record<string, any[]>;
  onSelectKind: (kind: string) => void;
}

export function SynthesisRelationsSection({
  summaries,
  relationsByKind,
  onSelectKind,
}: SynthesisRelationsSectionProps) {
  const { t } = useTranslation();
  const displaySummaries = summaries ?? Object.entries(relationsByKind).map(([kind, relations]) => {
    const relationArray = relations as any[];
    const supportingCount = relationArray.filter((relation) => relation.direction === "supports").length;
    const contradictingCount = relationArray.filter((relation) => relation.direction === "contradicts").length;
    return {
      kind,
      relation_count: relationArray.length,
      average_confidence: relationArray.reduce(
        (sum, relation) => sum + (relation.confidence || 0),
        0,
      ) / relationArray.length,
      supporting_count: supportingCount,
      contradicting_count: contradictingCount,
      neutral_count: relationArray.length - supportingCount - contradictingCount,
    };
  });

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        {t("synthesis.relations.title", "Relations by Type")}
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        {t("synthesis.relations.description", "Click any relation type to see details and explanation.")}
      </Typography>

      <Stack spacing={1}>
        {displaySummaries.map((summary) => {
          const relationArray = relationsByKind[summary.kind] || [];
          const kindConfidence = summary.average_confidence;

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
                    label={`${Math.round(kindConfidence * 100)}% confidence`}
                    size="small"
                    color={kindConfidence > 0.7 ? "success" : kindConfidence > 0.4 ? "warning" : "error"}
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <List dense>
                  {relationArray.map((relation, index) => (
                    <ListItem key={index} disablePadding>
                      <ListItemButton onClick={() => onSelectKind(summary.kind)}>
                        <ListItemText
                          primary={
                            <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                              <Typography variant="body2">
                                {relation.kind || summary.kind}
                              </Typography>
                              {relation.direction && (
                                <Chip
                                  label={relation.direction}
                                  size="small"
                                  color={relation.direction === "supports" ? "success" : "error"}
                                />
                              )}
                            </Box>
                          }
                          secondary={
                            relation.confidence !== undefined
                              ? t("synthesis.relation.confidence", "Confidence: {{value}}%", {
                                  value: Math.round(relation.confidence * 100),
                                })
                              : undefined
                          }
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          );
        })}
      </Stack>
    </Box>
  );
}

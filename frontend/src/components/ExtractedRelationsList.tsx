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
} from "../types/extraction";

interface ExtractedRelationsListProps {
  relations: ExtractedRelation[];
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
  other: <ScienceIcon fontSize="small" />,
};

export const ExtractedRelationsList: React.FC<ExtractedRelationsListProps> = ({
  relations,
  selectedRelations,
  onToggle,
}) => {
  if (relations.length === 0) {
    return (
      <Alert severity="info">
        No relations were extracted from the document.
      </Alert>
    );
  }

  return (
    <Stack spacing={2}>
      {relations.map((relation) => {
        const relationKey = `${relation.subject_slug}-${relation.relation_type}-${relation.object_slug}`;
        const isSelected = selectedRelations.has(relationKey);

        return (
          <Card
            key={relationKey}
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
                <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
                  <Checkbox
                    checked={isSelected}
                    onChange={() => onToggle(relationKey)}
                    sx={{ mt: -1 }}
                  />

                  <Box sx={{ flex: 1 }}>
                    {/* Subject -> Relation -> Object */}
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        flexWrap: "wrap",
                      }}
                    >
                      <Chip label={relation.subject_slug} variant="outlined" />
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
                        }}
                      >
                        {relationTypeIcons[relation.relation_type]}
                        <Typography variant="body2" fontWeight="medium">
                          {relationTypeLabels[relation.relation_type]}
                        </Typography>
                      </Box>
                      <Chip label={relation.object_slug} variant="outlined" />
                    </Box>

                    {/* Additional roles */}
                    {Object.keys(relation.roles).length > 0 && (
                      <Box sx={{ mt: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
                        {Object.entries(relation.roles).map(([role, value]) => (
                          <Chip
                            key={role}
                            label={`${role}: ${value}`}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: "0.75rem" }}
                          />
                        ))}
                      </Box>
                    )}

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
                  </Box>

                  {/* Confidence */}
                  <Chip
                    label={relation.confidence}
                    size="small"
                    color={confidenceColors[relation.confidence]}
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
                    ml: 5, // Align with content (after checkbox)
                  }}
                >
                  <Typography variant="body2" sx={{ fontStyle: "italic" }}>
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

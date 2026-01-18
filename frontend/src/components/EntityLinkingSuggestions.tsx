/**
 * EntityLinkingSuggestions component
 *
 * Displays extracted entities with linking suggestions and allows user to decide
 * whether to create new entities or link to existing ones.
 */
import React, { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  IconButton,
  Stack,
  Tooltip,
  ToggleButtonGroup,
  ToggleButton,
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import {
  Link as LinkIcon,
  AddCircle as AddCircleIcon,
  RemoveCircle as RemoveCircleIcon,
  CheckCircle as CheckCircleIcon,
  AutoFixHigh as AutoFixHighIcon,
  ViewList as ViewListIcon,
  ViewModule as ViewModuleIcon,
} from "@mui/icons-material";
import type {
  ExtractedEntity,
  EntityLinkMatch,
  EntityLinkingDecision,
  ConfidenceLevel,
  EntityCategory,
} from "../types/extraction";

interface EntityLinkingSuggestionsProps {
  entities: ExtractedEntity[];
  linkSuggestions: EntityLinkMatch[];
  decisions: Record<string, EntityLinkingDecision>;
  onDecisionChange: (slug: string, decision: EntityLinkingDecision) => void;
}

const confidenceColors: Record<ConfidenceLevel, "success" | "warning" | "error"> = {
  high: "success",
  medium: "warning",
  low: "error",
};

const categoryColors: Record<EntityCategory, string> = {
  drug: "#2196f3",
  disease: "#f44336",
  symptom: "#ff9800",
  biological_mechanism: "#9c27b0",
  treatment: "#4caf50",
  biomarker: "#00bcd4",
  population: "#795548",
  outcome: "#607d8b",
  other: "#9e9e9e",
};

export const EntityLinkingSuggestions: React.FC<EntityLinkingSuggestionsProps> = ({
  entities,
  linkSuggestions,
  decisions,
  onDecisionChange,
}) => {
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");

  const getSuggestionForEntity = (slug: string): EntityLinkMatch | undefined => {
    return linkSuggestions.find((s) => s.extracted_slug === slug);
  };

  const handleActionChange = (
    slug: string,
    action: "create" | "link" | "skip"
  ) => {
    const suggestion = getSuggestionForEntity(slug);

    onDecisionChange(slug, {
      extracted_slug: slug,
      action,
      linked_entity_id:
        action === "link" ? suggestion?.matched_entity_id || undefined : undefined,
    });
  };

  if (entities.length === 0) {
    return (
      <Alert severity="info">
        No entities were extracted from the document.
      </Alert>
    );
  }

  return (
    <Stack spacing={2}>
      {/* View Mode Toggle */}
      <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={(_, value) => value && setViewMode(value)}
          size="small"
        >
          <ToggleButton value="cards">
            <Tooltip title="Card view">
              <ViewModuleIcon />
            </Tooltip>
          </ToggleButton>
          <ToggleButton value="table">
            <Tooltip title="Compact table view">
              <ViewListIcon />
            </Tooltip>
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {viewMode === "table" ? (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Entity</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Confidence</TableCell>
                <TableCell>Match</TableCell>
                <TableCell align="right">Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {entities.map((entity) => {
                const suggestion = getSuggestionForEntity(entity.slug);
                const decision = decisions[entity.slug];

                return (
                  <TableRow key={entity.slug} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {entity.slug}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        "{entity.text_span}"
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={entity.category}
                        size="small"
                        sx={{
                          bgcolor: categoryColors[entity.category],
                          color: "white",
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={entity.confidence}
                        size="small"
                        color={confidenceColors[entity.confidence]}
                      />
                    </TableCell>
                    <TableCell>
                      {suggestion && suggestion.match_type !== "none" ? (
                        <Tooltip title={`${suggestion.matched_entity_slug} (${Math.round(suggestion.confidence * 100)}%)`}>
                          <Chip
                            label={suggestion.match_type}
                            size="small"
                            color={
                              suggestion.match_type === "exact"
                                ? "success"
                                : suggestion.match_type === "synonym"
                                ? "info"
                                : "warning"
                            }
                            icon={
                              suggestion.match_type === "exact" ? (
                                <CheckCircleIcon />
                              ) : (
                                <AutoFixHighIcon />
                              )
                            }
                          />
                        </Tooltip>
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          No match
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <ToggleButtonGroup
                        value={decision?.action || "create"}
                        exclusive
                        onChange={(_, value) => {
                          if (value !== null) {
                            handleActionChange(entity.slug, value);
                          }
                        }}
                        size="small"
                      >
                        <ToggleButton value="create">
                          <Tooltip title="Create new">
                            <AddCircleIcon fontSize="small" />
                          </Tooltip>
                        </ToggleButton>
                        {suggestion && suggestion.match_type !== "none" && (
                          <ToggleButton value="link">
                            <Tooltip title="Link to existing">
                              <LinkIcon fontSize="small" />
                            </Tooltip>
                          </ToggleButton>
                        )}
                        <ToggleButton value="skip">
                          <Tooltip title="Skip">
                            <RemoveCircleIcon fontSize="small" />
                          </Tooltip>
                        </ToggleButton>
                      </ToggleButtonGroup>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
    <Stack spacing={2}>
      {entities.map((entity) => {
        const suggestion = getSuggestionForEntity(entity.slug);
        const decision = decisions[entity.slug];

        return (
          <Card key={entity.slug} variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                {/* Entity header */}
                <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" component="div">
                      {entity.slug}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      {entity.summary}
                    </Typography>
                  </Box>

                  <Stack direction="row" spacing={1}>
                    <Chip
                      label={entity.category}
                      size="small"
                      sx={{
                        bgcolor: categoryColors[entity.category],
                        color: "white",
                      }}
                    />
                    <Chip
                      label={entity.confidence}
                      size="small"
                      color={confidenceColors[entity.confidence]}
                    />
                  </Stack>
                </Box>

                {/* Text span */}
                <Box
                  sx={{
                    p: 1.5,
                    bgcolor: "grey.50",
                    borderRadius: 1,
                    borderLeft: "3px solid",
                    borderColor: "primary.main",
                  }}
                >
                  <Typography variant="body2" sx={{ fontStyle: "italic" }}>
                    "{entity.text_span}"
                  </Typography>
                </Box>

                {/* Link suggestion */}
                {suggestion && suggestion.match_type !== "none" && (
                  <Alert
                    severity={
                      suggestion.match_type === "exact"
                        ? "success"
                        : suggestion.match_type === "synonym"
                        ? "info"
                        : "warning"
                    }
                    icon={
                      suggestion.match_type === "exact" ? (
                        <CheckCircleIcon />
                      ) : (
                        <AutoFixHighIcon />
                      )
                    }
                  >
                    <Box>
                      <Typography variant="body2" fontWeight="medium">
                        {suggestion.match_type === "exact"
                          ? "Exact match found"
                          : suggestion.match_type === "synonym"
                          ? "Synonym match found"
                          : "Similar entity found"}
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 0.5 }}>
                        Existing entity:{" "}
                        <strong>{suggestion.matched_entity_slug}</strong>
                        {" "}(confidence: {Math.round(suggestion.confidence * 100)}%)
                      </Typography>
                    </Box>
                  </Alert>
                )}

                {/* Action selector */}
                <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                  <ToggleButtonGroup
                    value={decision?.action || "create"}
                    exclusive
                    onChange={(_, value) => {
                      if (value !== null) {
                        handleActionChange(entity.slug, value);
                      }
                    }}
                    size="small"
                  >
                    <ToggleButton value="create">
                      <Tooltip title="Create as new entity">
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                          <AddCircleIcon fontSize="small" />
                          Create New
                        </Box>
                      </Tooltip>
                    </ToggleButton>

                    {suggestion && suggestion.match_type !== "none" && (
                      <ToggleButton value="link">
                        <Tooltip title={`Link to ${suggestion.matched_entity_slug}`}>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                            <LinkIcon fontSize="small" />
                            Link to Existing
                          </Box>
                        </Tooltip>
                      </ToggleButton>
                    )}

                    <ToggleButton value="skip">
                      <Tooltip title="Skip this entity">
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                          <RemoveCircleIcon fontSize="small" />
                          Skip
                        </Box>
                      </Tooltip>
                    </ToggleButton>
                  </ToggleButtonGroup>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        );
      })}
    </Stack>
      )}
    </Stack>
  );
};

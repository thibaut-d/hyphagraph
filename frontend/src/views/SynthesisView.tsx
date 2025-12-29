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

import { useEffect, useState } from "react";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Typography,
  Paper,
  Stack,
  CircularProgress,
  Alert,
  Box,
  Breadcrumbs,
  Link,
  Card,
  CardContent,
  Chip,
  Button,
  Grid,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningIcon from "@mui/icons-material/Warning";
import ErrorIcon from "@mui/icons-material/Error";
import InfoIcon from "@mui/icons-material/Info";

import { getEntity, EntityRead } from "../api/entities";
import { getInferenceForEntity } from "../api/inferences";
import { InferenceRead } from "../types/inference";
import { resolveLabel } from "../utils/i18nLabel";

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

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [inference, setInference] = useState<InferenceRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch entity and inferences
  useEffect(() => {
    if (!id) {
      setError("Missing entity ID");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([
      getEntity(id),
      getInferenceForEntity(id)
    ])
      .then(([entityData, inferenceData]) => {
        setEntity(entityData);
        setInference(inferenceData);
      })
      .catch((err) => {
        console.error("Failed to load synthesis:", err);
        setError(err.message || "Failed to load synthesis");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

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

  const entityLabel = resolveLabel(entity.label, entity.label_i18n, i18n.language);

  // Calculate synthesis statistics
  const relationsByKind = inference?.relations_by_kind || {};
  const totalRelations = Object.values(relationsByKind).reduce(
    (sum, relations: any[]) => sum + relations.length,
    0
  );

  // Count unique sources
  const uniqueSources = new Set<string>();
  Object.values(relationsByKind).forEach((relations: any[]) => {
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

  Object.values(relationsByKind).forEach((relations: any[]) => {
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

  const averageConfidence = confidenceCount > 0 ? totalConfidence / confidenceCount : 0;

  const hasData = totalRelations > 0;

  return (
    <Stack spacing={3}>
      {/* Breadcrumbs */}
      <Breadcrumbs>
        <Link component={RouterLink} to="/entities" underline="hover">
          {t("menu.entities", "Entities")}
        </Link>
        <Link component={RouterLink} to={`/entities/${id}`} underline="hover">
          {entityLabel}
        </Link>
        <Typography color="text.primary">
          {t("synthesis.title", "Synthesis")}
        </Typography>
      </Breadcrumbs>

      {/* Back button */}
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/entities/${id}`)}
          variant="outlined"
          size="small"
        >
          {t("common.back", "Back to entity")}
        </Button>
      </Box>

      {/* Header */}
      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h4" component="h1">
            {t("synthesis.header", "Knowledge Synthesis")}
          </Typography>
          <Typography variant="h6" color="text.secondary">
            {entityLabel}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("synthesis.description",
              "Comprehensive view of all computed knowledge about this entity, including consensus levels and evidence quality."
            )}
          </Typography>
        </Stack>
      </Paper>

      {hasData ? (
        <>
          {/* Statistics Overview */}
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    {t("synthesis.stats.relations", "Total Relations")}
                  </Typography>
                  <Typography variant="h4">
                    {totalRelations}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    {t("synthesis.stats.sources", "Unique Sources")}
                  </Typography>
                  <Typography variant="h4">
                    {uniqueSources.size}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    {t("synthesis.stats.confidence", "Avg. Confidence")}
                  </Typography>
                  <Typography variant="h4">
                    {Math.round(averageConfidence * 100)}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={averageConfidence * 100}
                    sx={{ mt: 1 }}
                  />
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    {t("synthesis.stats.kinds", "Relation Types")}
                  </Typography>
                  <Typography variant="h4">
                    {Object.keys(relationsByKind).length}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Quality Indicators */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                {t("synthesis.quality.title", "Evidence Quality Overview")}
              </Typography>
              <Stack spacing={2}>
                <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                  <Chip
                    icon={<CheckCircleIcon />}
                    label={t("synthesis.quality.high", "High Confidence: {{count}}", { count: highConfidenceCount })}
                    color="success"
                  />
                  <Chip
                    icon={<InfoIcon />}
                    label={t("synthesis.quality.total", "Total: {{count}}", { count: confidenceCount })}
                    variant="outlined"
                  />
                  {lowConfidenceCount > 0 && (
                    <Chip
                      icon={<WarningIcon />}
                      label={t("synthesis.quality.low", "Low Confidence: {{count}}", { count: lowConfidenceCount })}
                      color="warning"
                    />
                  )}
                  {contradictionCount > 0 && (
                    <Chip
                      icon={<ErrorIcon />}
                      label={t("synthesis.quality.contradictions", "Contradictions: {{count}}", { count: contradictionCount })}
                      color="error"
                    />
                  )}
                </Box>
              </Stack>
            </CardContent>
          </Card>

          {/* Relations by Kind */}
          <Box>
            <Typography variant="h5" gutterBottom>
              {t("synthesis.relations.title", "Relations by Type")}
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              {t("synthesis.relations.description",
                "Click any relation type to see details and explanation."
              )}
            </Typography>

            <Stack spacing={1}>
              {Object.entries(relationsByKind).map(([kind, relations]: [string, any]) => {
                const relationArray = relations as any[];
                const kindConfidence = relationArray.reduce(
                  (sum, rel) => sum + (rel.confidence || 0),
                  0
                ) / relationArray.length;

                return (
                  <Accordion key={kind}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 2, width: "100%" }}>
                        <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                          {kind}
                        </Typography>
                        <Chip
                          label={`${relationArray.length} relation${relationArray.length !== 1 ? 's' : ''}`}
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
                            <ListItemButton
                              onClick={() => navigate(`/entities/${id}/properties/${kind}`)}
                            >
                              <ListItemText
                                primary={
                                  <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                                    <Typography variant="body2">
                                      {relation.kind || kind}
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
                                        value: Math.round(relation.confidence * 100)
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

          {/* Knowledge Gaps */}
          {Object.keys(relationsByKind).length < 3 && (
            <Card sx={{ borderColor: "warning.main", borderWidth: 1, borderStyle: "dashed" }}>
              <CardContent>
                <Stack spacing={2}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <InfoIcon color="warning" />
                    <Typography variant="h6" color="warning.main">
                      {t("synthesis.gaps.title", "Knowledge Gaps Detected")}
                    </Typography>
                  </Box>
                  <Typography variant="body2">
                    {t("synthesis.gaps.description",
                      "This entity has limited relation types. Consider adding more evidence or relations to improve knowledge coverage."
                    )}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* Action Buttons */}
          <Divider />
          <Box sx={{ display: "flex", gap: 2, justifyContent: "center", flexWrap: "wrap" }}>
            {contradictionCount > 0 && (
              <Button
                variant="contained"
                color="error"
                onClick={() => navigate(`/entities/${id}/disagreements`)}
              >
                {t("synthesis.view_disagreements", "View Disagreements ({{count}})", { count: contradictionCount })}
              </Button>
            )}
            <Button
              variant="outlined"
              onClick={() => navigate(`/entities/${id}`)}
            >
              {t("synthesis.back_to_detail", "Back to Entity Detail")}
            </Button>
          </Box>
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

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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import WarningIcon from "@mui/icons-material/Warning";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import InfoIcon from "@mui/icons-material/Info";

import { getEntity, EntityRead } from "../api/entities";
import { getInferences, InferenceRead } from "../api/inferences";
import { listRelations, RelationRead } from "../api/relations";
import { resolveLabel } from "../utils/i18nLabel";

interface DisagreementGroup {
  roleType: string;
  supporting: RelationRead[];
  contradicting: RelationRead[];
  confidence: number;
}

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

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [inference, setInference] = useState<InferenceRead | null>(null);
  const [relations, setRelations] = useState<RelationRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch entity, inferences, and relations
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
      getInferences(id),
      listRelations({ entity_id: id, limit: 1000 })
    ])
      .then(([entityData, inferenceData, relationsData]) => {
        setEntity(entityData);
        setInference(inferenceData);
        setRelations(relationsData.items);
      })
      .catch((err) => {
        console.error("Failed to load disagreements:", err);
        setError(err.message || "Failed to load disagreements");
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

  const entityLabel = resolveLabel(entity.label, entity.label_i18n, i18n.language);

  // Group relations by role type and direction
  const disagreementGroups: DisagreementGroup[] = [];

  if (inference && inference.relations_by_kind) {
    Object.entries(inference.relations_by_kind).forEach(([roleType, roleRelations]: [string, any]) => {
      const relationArray = roleRelations as any[];

      const supporting = relationArray.filter(rel =>
        rel.direction === "supports" || !rel.direction
      );
      const contradicting = relationArray.filter(rel =>
        rel.direction === "contradicts"
      );

      // Only include if there are contradictions
      if (contradicting.length > 0) {
        const totalConfidence = relationArray.reduce(
          (sum, rel) => sum + (rel.confidence || 0),
          0
        ) / relationArray.length;

        disagreementGroups.push({
          roleType,
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
      {/* Breadcrumbs */}
      <Breadcrumbs>
        <Link component={RouterLink} to="/entities" underline="hover">
          {t("menu.entities", "Entities")}
        </Link>
        <Link component={RouterLink} to={`/entities/${id}`} underline="hover">
          {entityLabel}
        </Link>
        <Typography color="text.primary">
          {t("disagreements.title", "Disagreements")}
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
      <Paper sx={{ p: 3, borderColor: "error.main", borderWidth: 2, borderStyle: "solid" }}>
        <Stack spacing={2}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <WarningIcon color="error" sx={{ fontSize: 40 }} />
            <Typography variant="h4" component="h1" color="error">
              {t("disagreements.header", "Contradictory Evidence")}
            </Typography>
          </Box>
          <Typography variant="h6" color="text.secondary">
            {entityLabel}
          </Typography>
          <Alert severity="warning">
            <Typography variant="body2">
              {t("disagreements.honesty_principle",
                "⚠️ Scientific Honesty: We never hide contradictions. All conflicting evidence is shown here to enable informed decision-making."
              )}
            </Typography>
          </Alert>
        </Stack>
      </Paper>

      {hasDisagreements ? (
        <>
          {/* Summary */}
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    {t("disagreements.stats.types", "Conflicting Relation Types")}
                  </Typography>
                  <Typography variant="h4">
                    {disagreementGroups.length}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    {t("disagreements.stats.total", "Total Contradictions")}
                  </Typography>
                  <Typography variant="h4" color="error">
                    {totalContradictions}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Disagreement Groups */}
          <Box>
            <Typography variant="h5" gutterBottom>
              {t("disagreements.groups.title", "Contradictions by Relation Type")}
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              {t("disagreements.groups.description",
                "Each section shows supporting evidence vs. contradicting evidence side-by-side."
              )}
            </Typography>

            <Stack spacing={2}>
              {disagreementGroups.map((group, index) => (
                <Accordion key={index} defaultExpanded={index === 0}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 2, width: "100%" }}>
                      <Typography variant="h6" sx={{ flexGrow: 1 }}>
                        {group.roleType}
                      </Typography>
                      <Chip
                        icon={<ThumbUpIcon />}
                        label={`${group.supporting.length} supporting`}
                        color="success"
                        size="small"
                      />
                      <Chip
                        icon={<ThumbDownIcon />}
                        label={`${group.contradicting.length} contradicting`}
                        color="error"
                        size="small"
                      />
                      <Chip
                        label={`${Math.round(group.confidence * 100)}% confidence`}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      {/* Supporting Evidence */}
                      <Grid item xs={12} md={6}>
                        <Card sx={{ borderColor: "success.main", borderWidth: 1, borderStyle: "solid" }}>
                          <CardContent>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                              <ThumbUpIcon color="success" />
                              <Typography variant="h6" color="success.main">
                                {t("disagreements.supporting", "Supporting ({{count}})", { count: group.supporting.length })}
                              </Typography>
                            </Box>

                            {group.supporting.length > 0 ? (
                              <TableContainer>
                                <Table size="small">
                                  <TableHead>
                                    <TableRow>
                                      <TableCell>{t("disagreements.table.kind", "Kind")}</TableCell>
                                      <TableCell>{t("disagreements.table.confidence", "Confidence")}</TableCell>
                                      <TableCell>{t("disagreements.table.source", "Source")}</TableCell>
                                    </TableRow>
                                  </TableHead>
                                  <TableBody>
                                    {group.supporting.map((relation, idx) => (
                                      <TableRow key={idx}>
                                        <TableCell>{relation.kind || group.roleType}</TableCell>
                                        <TableCell>
                                          {relation.confidence !== undefined
                                            ? `${Math.round(relation.confidence * 100)}%`
                                            : "-"}
                                        </TableCell>
                                        <TableCell>
                                          <Link
                                            component={RouterLink}
                                            to={`/sources/${relation.source_id}`}
                                            variant="body2"
                                          >
                                            View Source
                                          </Link>
                                        </TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </TableContainer>
                            ) : (
                              <Typography variant="body2" color="text.secondary">
                                {t("disagreements.no_supporting", "No supporting evidence")}
                              </Typography>
                            )}
                          </CardContent>
                        </Card>
                      </Grid>

                      {/* Contradicting Evidence */}
                      <Grid item xs={12} md={6}>
                        <Card sx={{ borderColor: "error.main", borderWidth: 1, borderStyle: "solid" }}>
                          <CardContent>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                              <ThumbDownIcon color="error" />
                              <Typography variant="h6" color="error.main">
                                {t("disagreements.contradicting", "Contradicting ({{count}})", { count: group.contradicting.length })}
                              </Typography>
                            </Box>

                            <TableContainer>
                              <Table size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell>{t("disagreements.table.kind", "Kind")}</TableCell>
                                    <TableCell>{t("disagreements.table.confidence", "Confidence")}</TableCell>
                                    <TableCell>{t("disagreements.table.source", "Source")}</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {group.contradicting.map((relation, idx) => (
                                    <TableRow key={idx}>
                                      <TableCell>{relation.kind || group.roleType}</TableCell>
                                      <TableCell>
                                        {relation.confidence !== undefined
                                          ? `${Math.round(relation.confidence * 100)}%`
                                          : "-"}
                                      </TableCell>
                                      <TableCell>
                                        <Link
                                          component={RouterLink}
                                          to={`/sources/${relation.source_id}`}
                                          variant="body2"
                                        >
                                          View Source
                                        </Link>
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          </CardContent>
                        </Card>
                      </Grid>
                    </Grid>

                    {/* Explanation Link */}
                    <Box sx={{ mt: 2, display: "flex", justifyContent: "center" }}>
                      <Button
                        variant="outlined"
                        onClick={() => navigate(`/entities/${id}/properties/${group.roleType}`)}
                      >
                        {t("disagreements.view_explanation", "View Detailed Explanation")}
                      </Button>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Stack>
          </Box>

          {/* Guidance */}
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
                <InfoIcon color="primary" />
                <Stack spacing={1}>
                  <Typography variant="h6">
                    {t("disagreements.guidance.title", "How to Interpret Disagreements")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t("disagreements.guidance.text",
                      "• Contradictions are normal in science - they indicate evolving knowledge.\n" +
                      "• Check source quality and publication dates - newer studies may supersede older ones.\n" +
                      "• Look for methodological differences - studies with different designs may reach different conclusions.\n" +
                      "• Consult domain experts when making critical decisions based on contradictory evidence."
                    ).split('\n').map((line, i) => (
                      <Typography key={i} variant="body2" component="div">
                        {line}
                      </Typography>
                    ))}
                  </Typography>
                </Stack>
              </Box>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <Divider />
          <Box sx={{ display: "flex", gap: 2, justifyContent: "center", flexWrap: "wrap" }}>
            <Button
              variant="outlined"
              onClick={() => navigate(`/entities/${id}/synthesis`)}
            >
              {t("disagreements.view_synthesis", "View Full Synthesis")}
            </Button>
            <Button
              variant="outlined"
              onClick={() => navigate(`/entities/${id}`)}
            >
              {t("disagreements.back_to_detail", "Back to Entity Detail")}
            </Button>
          </Box>
        </>
      ) : (
        <Alert severity="success" icon={<ThumbUpIcon />}>
          <Typography variant="body1" gutterBottom>
            {t("disagreements.no_data.title", "No contradictions detected")}
          </Typography>
          <Typography variant="body2">
            {t("disagreements.no_data.description",
              "All available evidence for this entity is consistent. This suggests strong consensus, though limited evidence diversity may also explain the lack of contradictions."
            )}
          </Typography>
        </Alert>
      )}
    </Stack>
  );
}

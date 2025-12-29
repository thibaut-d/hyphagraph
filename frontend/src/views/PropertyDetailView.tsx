/**
 * PropertyDetailView
 *
 * Dedicated view for explaining a specific property or relation.
 * Shows how a conclusion is established with evidence traceability.
 *
 * Purpose (from UX.md):
 * - Explain HOW a conclusion is established
 * - Show consensus status
 * - Display score (if applicable)
 * - List known limitations
 * - Provide access to evidence
 *
 * Navigation: Entity Detail → Property/Inference → This View
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
  Divider,
  List,
  ListItem,
  ListItemText,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningIcon from "@mui/icons-material/Warning";
import ErrorIcon from "@mui/icons-material/Error";

import { getExplanation, ExplanationRead } from "../api/explanations";
import { getEntity, EntityRead } from "../api/entities";
import { EvidenceTrace } from "../components/EvidenceTrace";
import { resolveLabel } from "../utils/i18nLabel";

/**
 * PropertyDetailView Component
 *
 * Displays detailed information about a specific property/inference:
 * - What is the conclusion?
 * - How strong is the consensus?
 * - What is the evidence quality?
 * - What are the limitations?
 * - Full evidence chain
 */
export function PropertyDetailView() {
  const { entityId, roleType } = useParams<{ entityId: string; roleType: string }>();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [explanation, setExplanation] = useState<ExplanationRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch entity and explanation
  useEffect(() => {
    if (!entityId || !roleType) {
      setError("Missing entity ID or role type");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([
      getEntity(entityId),
      getExplanation(entityId, roleType)
    ])
      .then(([entityData, explanationData]) => {
        setEntity(entityData);
        setExplanation(explanationData);
      })
      .catch((err) => {
        console.error("Failed to load property details:", err);
        setError(err.message || "Failed to load property details");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [entityId, roleType]);

  // Loading state
  if (loading) {
    return (
      <Stack alignItems="center" mt={4}>
        <CircularProgress />
        <Typography variant="body2" color="text.secondary" mt={2}>
          {t("property.loading", "Loading property details...")}
        </Typography>
      </Stack>
    );
  }

  // Error state
  if (error || !explanation || !entity) {
    return (
      <Alert severity="error">
        {error || t("common.error", "An error occurred")}
      </Alert>
    );
  }

  const entityLabel = resolveLabel(entity.label, entity.label_i18n, i18n.language);

  // Determine consensus status based on confidence and contradictions
  const hasContradictions = explanation.contradictions && explanation.contradictions.length > 0;
  const isHighConfidence = (explanation.confidence || 0) > 0.7;
  const isMediumConfidence = (explanation.confidence || 0) > 0.4;

  const consensusStatus = hasContradictions
    ? "disputed"
    : isHighConfidence
    ? "strong"
    : isMediumConfidence
    ? "moderate"
    : "weak";

  const consensusConfig = {
    strong: {
      label: t("property.consensus.strong", "Strong Consensus"),
      color: "success" as const,
      icon: <CheckCircleIcon />,
    },
    moderate: {
      label: t("property.consensus.moderate", "Moderate Consensus"),
      color: "warning" as const,
      icon: <WarningIcon />,
    },
    weak: {
      label: t("property.consensus.weak", "Weak Evidence"),
      color: "error" as const,
      icon: <ErrorIcon />,
    },
    disputed: {
      label: t("property.consensus.disputed", "Disputed / Contradictory"),
      color: "error" as const,
      icon: <WarningIcon />,
    },
  };

  const consensus = consensusConfig[consensusStatus];

  // Score display
  const scoreColor = explanation.score
    ? explanation.score > 0.3
      ? "success"
      : explanation.score < -0.3
      ? "error"
      : "warning"
    : "default";

  return (
    <Stack spacing={3}>
      {/* Breadcrumbs */}
      <Breadcrumbs>
        <Link component={RouterLink} to="/entities" underline="hover">
          {t("menu.entities", "Entities")}
        </Link>
        <Link component={RouterLink} to={`/entities/${entityId}`} underline="hover">
          {entityLabel}
        </Link>
        <Typography color="text.primary">
          {roleType}
        </Typography>
      </Breadcrumbs>

      {/* Back button */}
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/entities/${entityId}`)}
          variant="outlined"
          size="small"
        >
          {t("common.back", "Back to entity")}
        </Button>
      </Box>

      {/* Property Header */}
      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h4" component="h1">
            {t("property.title", "Property: {{roleType}}", { roleType })}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            {t("property.subtitle", "For entity: {{entity}}", { entity: entityLabel })}
          </Typography>

          {/* Consensus Status */}
          <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
            <Chip
              icon={consensus.icon}
              label={consensus.label}
              color={consensus.color}
              size="medium"
            />
            {explanation.confidence !== undefined && (
              <Chip
                label={t("property.confidence", "Confidence: {{value}}%", {
                  value: Math.round(explanation.confidence * 100),
                })}
                variant="outlined"
              />
            )}
          </Box>
        </Stack>
      </Paper>

      {/* Conclusion Summary */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {t("property.conclusion", "Conclusion")}
          </Typography>

          {explanation.score !== undefined && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {t("property.score_label", "Computed Score")}
              </Typography>
              <Chip
                label={explanation.score.toFixed(3)}
                color={scoreColor}
                size="medium"
              />
            </Box>
          )}

          {explanation.natural_language_summary && (
            <Box>
              <Typography variant="body1" sx={{ fontStyle: "italic", color: "text.secondary" }}>
                {explanation.natural_language_summary}
              </Typography>
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                {t("property.summary_disclaimer", "⚠️ This is a generated summary. See evidence below for source data.")}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Known Limitations */}
      {(hasContradictions || explanation.confidence < 0.7) && (
        <Card>
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="h6">
                {t("property.limitations", "Known Limitations")}
              </Typography>

              <List dense>
                {!isHighConfidence && (
                  <ListItem>
                    <ListItemText
                      primary={t("property.limitation.confidence", "Limited evidence quality")}
                      secondary={t("property.limitation.confidence_detail",
                        "Confidence level is {{value}}% - consider this conclusion provisional.",
                        { value: Math.round((explanation.confidence || 0) * 100) }
                      )}
                    />
                  </ListItem>
                )}

                {hasContradictions && (
                  <ListItem>
                    <ListItemText
                      primary={t("property.limitation.contradictions", "Contradictory evidence exists")}
                      secondary={t("property.limitation.contradictions_detail",
                        "{{count}} source(s) contradict this conclusion. See contradictions section below.",
                        { count: explanation.contradictions.length }
                      )}
                    />
                  </ListItem>
                )}

                {explanation.evidence_chain && explanation.evidence_chain.length < 3 && (
                  <ListItem>
                    <ListItemText
                      primary={t("property.limitation.sources", "Limited source diversity")}
                      secondary={t("property.limitation.sources_detail",
                        "Only {{count}} source(s) support this conclusion.",
                        { count: explanation.evidence_chain.length }
                      )}
                    />
                  </ListItem>
                )}
              </List>
            </Stack>
          </CardContent>
        </Card>
      )}

      {/* Contradictions */}
      {hasContradictions && (
        <Card sx={{ borderColor: "error.main", borderWidth: 2, borderStyle: "solid" }}>
          <CardContent>
            <Stack spacing={2}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <WarningIcon color="error" />
                <Typography variant="h6" color="error">
                  {t("property.contradictions", "Contradictory Evidence")}
                </Typography>
              </Box>

              <Alert severity="error">
                {t("property.contradictions_warning",
                  "The following sources contradict this conclusion. Scientific honesty requires showing all evidence."
                )}
              </Alert>

              <List>
                {explanation.contradictions.map((contradiction, index) => (
                  <ListItem key={index}>
                    <ListItemText
                      primary={contradiction.detail || t("property.contradiction_detail", "Contradiction detected")}
                      secondary={contradiction.source_count
                        ? t("property.contradiction_sources", "{{count}} source(s)", { count: contradiction.source_count })
                        : undefined
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </Stack>
          </CardContent>
        </Card>
      )}

      <Divider />

      {/* Evidence Chain */}
      <Box>
        <Typography variant="h5" gutterBottom>
          {t("property.evidence", "Supporting Evidence")}
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          {t("property.evidence_description",
            "Complete chain of evidence supporting this conclusion. Click any source to view details."
          )}
        </Typography>

        {explanation.evidence_chain && explanation.evidence_chain.length > 0 ? (
          <EvidenceTrace evidence={explanation.evidence_chain} />
        ) : (
          <Alert severity="warning">
            {t("property.no_evidence", "No evidence chain available")}
          </Alert>
        )}
      </Box>

      {/* View All Evidence Button */}
      <Box sx={{ display: "flex", justifyContent: "center" }}>
        <Button
          variant="outlined"
          onClick={() => navigate(`/entities/${entityId}/properties/${roleType}/evidence`)}
        >
          {t("property.view_all_evidence", "View All Related Evidence")}
        </Button>
      </Box>
    </Stack>
  );
}

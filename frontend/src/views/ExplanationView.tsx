/**
 * Explanation View
 *
 * Displays detailed explanation of a computed inference,
 * including natural language summary, confidence breakdown,
 * contradictions, and full source chain.
 *
 * Enables ≤2 click traceability: Entity → Explain → Source
 */

import { useEffect, useState } from "react";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Typography,
  Paper,
  Stack,
  CircularProgress,
  Chip,
  Alert,
  Box,
  Breadcrumbs,
  Link,
  Card,
  CardContent,
  LinearProgress,
  Divider,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import WarningIcon from "@mui/icons-material/Warning";
import InfoIcon from "@mui/icons-material/Info";

import { getExplanation, ExplanationRead } from "../api/explanations";
import { EvidenceTrace } from "../components/EvidenceTrace";


export function ExplanationView() {
  const { entityId, roleType } = useParams<{ entityId: string; roleType: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [explanation, setExplanation] = useState<ExplanationRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!entityId || !roleType) {
      setError("Missing entity ID or role type");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    getExplanation(entityId, roleType)
      .then((data) => {
        setExplanation(data);
      })
      .catch((err) => {
        console.error("Failed to load explanation:", err);
        setError(err.message || "Failed to load explanation");
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
          {t("explanation.loading", "Generating explanation...")}
        </Typography>
      </Stack>
    );
  }

  // Error state
  if (error || !explanation) {
    return (
      <Alert severity="error">
        {error || t("common.error", "An error occurred")}
      </Alert>
    );
  }

  // Score color based on value
  const scoreColor = explanation.score
    ? explanation.score > 0.3
      ? "success"
      : explanation.score < -0.3
      ? "error"
      : "warning"
    : "default";

  // Confidence color
  const confidenceColor =
    explanation.confidence > 0.7
      ? "success"
      : explanation.confidence > 0.4
      ? "warning"
      : "error";

  return (
    <Stack spacing={3}>
      {/* Breadcrumb Navigation */}
      <Breadcrumbs>
        <Link
          component={RouterLink}
          to={`/entities/${entityId}`}
          underline="hover"
          color="inherit"
        >
          {t("common.back_to_entity", "Back to Entity")}
        </Link>
        <Typography color="text.primary">
          {t("explanation.title", "Inference Explanation")}
        </Typography>
      </Breadcrumbs>

      {/* Header */}
      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <ArrowBackIcon
              sx={{ cursor: "pointer" }}
              onClick={() => navigate(`/entities/${entityId}`)}
            />
            <div>
              <Typography variant="h4">
                {t("explanation.header", "Inference Explanation")}
              </Typography>
              <Typography variant="subtitle1" color="text.secondary">
                {t("explanation.role_type", "Role")}: <strong>{roleType}</strong>
              </Typography>
            </div>
          </Stack>

          {/* Score Overview Chips */}
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Chip
              label={`${t("explanation.score", "Score")}: ${
                explanation.score !== null ? explanation.score.toFixed(2) : "N/A"
              }`}
              color={scoreColor}
              variant="outlined"
            />
            <Chip
              label={`${t("explanation.confidence", "Confidence")}: ${(
                explanation.confidence * 100
              ).toFixed(0)}%`}
              color={confidenceColor}
              variant="outlined"
            />
            <Chip
              label={`${t("explanation.disagreement", "Disagreement")}: ${(
                explanation.disagreement * 100
              ).toFixed(0)}%`}
              color={explanation.disagreement > 0.3 ? "warning" : "default"}
              variant="outlined"
            />
          </Stack>
        </Stack>
      </Paper>

      {/* Natural Language Summary */}
      <Paper sx={{ p: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" mb={2}>
          <InfoIcon color="primary" />
          <Typography variant="h5">
            {t("explanation.summary_title", "Summary")}
          </Typography>
        </Stack>
        <Typography variant="body1">{explanation.summary}</Typography>
      </Paper>

      {/* Confidence Breakdown */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          {t("explanation.confidence_breakdown", "Confidence Breakdown")}
        </Typography>
        <Stack spacing={2} mt={2}>
          {explanation.confidence_factors.map((factor, idx) => (
            <Card key={idx} variant="outlined">
              <CardContent>
                <Stack spacing={1}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="h6">{factor.factor}</Typography>
                    <Typography variant="h6" color="primary">
                      {factor.value.toFixed(2)}
                    </Typography>
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {factor.explanation}
                  </Typography>
                  {factor.factor === "Confidence" && (
                    <Box sx={{ mt: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={factor.value * 100}
                        color={confidenceColor}
                        sx={{ height: 8, borderRadius: 1 }}
                      />
                    </Box>
                  )}
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      </Paper>

      {/* Contradictions (if any) */}
      {explanation.contradictions && explanation.disagreement > 0.1 && (
        <Paper sx={{ p: 3 }}>
          <Stack direction="row" spacing={1} alignItems="center" mb={2}>
            <WarningIcon color="warning" />
            <Typography variant="h5">
              {t("explanation.contradictions_title", "Contradictory Evidence")}
            </Typography>
          </Stack>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {explanation.disagreement > 0.5
              ? t(
                  "explanation.high_disagreement",
                  "High disagreement detected - sources significantly contradict each other"
                )
              : t(
                  "explanation.moderate_disagreement",
                  "Some disagreement detected among sources"
                )}
          </Alert>
          <Typography variant="body2" color="text.secondary">
            {t(
              "explanation.contradictions_note",
              "The sources below show opposing evidence. Review them carefully to understand the full picture."
            )}
          </Typography>
        </Paper>
      )}

      {/* Source Chain (Evidence Trace) */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          {t("explanation.source_evidence", "Source Evidence")}
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          {t(
            "explanation.source_evidence_desc",
            "Click on any source to view its full details"
          )}
        </Typography>
        <Divider sx={{ my: 2 }} />
        <EvidenceTrace sourceChain={explanation.source_chain} />
      </Paper>

      {/* Scope Filter Info (if applied) */}
      {explanation.scope_filter && Object.keys(explanation.scope_filter).length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            {t("explanation.scope_filter", "Applied Scope Filter")}
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {Object.entries(explanation.scope_filter).map(([key, value]) => (
              <Chip
                key={key}
                label={`${key}: ${value}`}
                size="small"
                color="primary"
                variant="outlined"
              />
            ))}
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}

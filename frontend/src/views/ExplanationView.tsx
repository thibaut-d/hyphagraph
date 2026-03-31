/**
 * Explanation View
 *
 * Displays detailed explanation of a computed inference,
 * including natural language summary, confidence breakdown,
 * contradictions, and full source chain.
 *
 * Enables ≤2 click traceability: Entity → Explain → Source
 */

import { useCallback } from "react";
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

import { getExplanation, ExplanationRead, formatExplanationSummary } from "../api/explanations";
import { EvidenceTrace } from "../components/EvidenceTrace";
import { useNotification } from "../notifications/NotificationContext";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";

function ContradictionEvidenceSection({
  title,
  description,
  sourceChain,
}: {
  title: string;
  description: string;
  sourceChain: ExplanationRead["source_chain"];
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          {description}
        </Typography>
        <EvidenceTrace sourceChain={sourceChain} />
      </CardContent>
    </Card>
  );
}

export function ExplanationView() {
  const { entityId, roleType } = useParams<{ entityId: string; roleType: string }>();
  const { t } = useTranslation();
  const { showError } = useNotification();
  const navigate = useNavigate();
  const handlePageError = usePageErrorHandler();

  const loadExplanation = useCallback(async (): Promise<ExplanationRead> => {
    if (!entityId || !roleType) {
      throw new Error("Missing entity ID or role type");
    }

    return getExplanation(entityId, roleType);
  }, [entityId, roleType]);

  const {
    data: explanation,
    loading,
    error,
  } = useAsyncResource<ExplanationRead>({
    enabled: true,
    deps: [entityId, roleType],
    load: loadExplanation,
    onError: (err) => {
      if (!entityId || !roleType) {
        const message = "Missing entity ID or role type";
        showError(message);
        return message;
      }

      return handlePageError(err, "Failed to load explanation").userMessage;
    },
  });

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
  const scoreColor = explanation.score !== null
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
  const contradictions = explanation.contradictions;
  const hasContradictions =
    contradictions &&
    (contradictions.supporting_sources.length > 0 || contradictions.contradicting_sources.length > 0) &&
    explanation.disagreement > 0.1;

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
          <Alert severity="info">
            {t(
              "explanation.reading_note",
              "Use this page to inspect how the score was computed. The summary is a reading of the evidence, and the source sections below show what supports or challenges it."
            )}
          </Alert>
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
        <Typography variant="body1">{formatExplanationSummary(explanation.summary, t)}</Typography>
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
      {hasContradictions && (
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
              "The evidence is separated below so you can compare what supports the reading versus what pushes against it."
            )}
          </Typography>
          <Stack spacing={2} mt={3}>
            <ContradictionEvidenceSection
              title={t("explanation.supporting_sources", {
                defaultValue: "Supporting evidence ({{count}})",
                count: contradictions.supporting_sources.length,
              })}
              description={t(
                "explanation.supporting_sources_desc",
                "These sources contribute evidence in the same direction as the computed reading."
              )}
              sourceChain={contradictions.supporting_sources}
            />
            <ContradictionEvidenceSection
              title={t("explanation.contradicting_sources", {
                defaultValue: "Contradicting evidence ({{count}})",
                count: contradictions.contradicting_sources.length,
              })}
              description={t(
                "explanation.contradicting_sources_desc",
                "These sources challenge the computed reading and are the main reason disagreement remains visible."
              )}
              sourceChain={contradictions.contradicting_sources}
            />
          </Stack>
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

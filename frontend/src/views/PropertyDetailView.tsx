/**
 * PropertyDetailView
 *
 * Dedicated view for a specific inferred property/role.
 * Uses the current explanation API contract.
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

import { getExplanation, ExplanationRead, formatExplanationSummary } from "../api/explanations";
import { getEntity } from "../api/entities";
import type { EntityRead } from "../types/entity";
import { EvidenceTrace } from "../components/EvidenceTrace";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";
import { entityPath, entitySubpath } from "../utils/entityPath";

export function PropertyDetailView() {
  const { id, roleType } = useParams<{ id: string; roleType: string }>();
  const { t } = useTranslation();
  const handlePageError = usePageErrorHandler();
  const navigate = useNavigate();

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [explanation, setExplanation] = useState<ExplanationRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!id || !roleType) {
      setError("Missing entity ID or role type");
      handlePageError(new Error("Missing entity ID or role type"), "Missing entity ID or role type");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    getEntity(id)
      .then(async (entityData) => {
        const explanationData = await getExplanation(entityData.id, roleType);
        setEntity(entityData);
        setExplanation(explanationData);
      })
      .catch((err) => {
        console.error("Failed to load property details:", err);
        const parsedError = handlePageError(err, "Failed to load property details");
        setEntity(null);
        setExplanation(null);
        setError(parsedError.userMessage);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [handlePageError, id, roleType]);

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

  if (error || !explanation || !entity || !id || !roleType) {
    return <Alert severity="error">{error || t("common.error", "An error occurred")}</Alert>;
  }

  const entityLabel = entity.slug;
  const canonicalEntityPath = entityPath(entity);

  const contradictionDetail = explanation.contradictions;
  const hasContradictions =
    Boolean(contradictionDetail) &&
    ((contradictionDetail?.supporting_sources.length || 0) > 0 ||
      (contradictionDetail?.contradicting_sources.length || 0) > 0);

  const isHighConfidence = explanation.confidence > 0.7;
  const isMediumConfidence = explanation.confidence > 0.4;

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

  const scoreColor =
    explanation.score === null
      ? "default"
      : explanation.score > 0.3
        ? "success"
        : explanation.score < -0.3
          ? "error"
          : "warning";

  const limitations: string[] = [];

  if (!isHighConfidence) {
    limitations.push(
      t(
        "property.limitation.confidence_detail",
        "Confidence is {{value}}%: interpret this conclusion with caution.",
        { value: Math.round(explanation.confidence * 100) },
      ),
    );
  }

  if (hasContradictions) {
    limitations.push(
      t(
        "property.limitation.contradictions_detail",
        "Conflicting sources exist and increase uncertainty.",
      ),
    );
  }

  if (explanation.source_chain.length < 3) {
    limitations.push(
      t(
        "property.limitation.sources_detail",
        "Limited source diversity ({{count}} source(s)).",
        { count: explanation.source_chain.length },
      ),
    );
  }

  return (
    <Stack spacing={3}>
      <Breadcrumbs>
        <Link component={RouterLink} to="/entities" underline="hover">
          {t("menu.entities", "Entities")}
        </Link>
        <Link component={RouterLink} to={canonicalEntityPath} underline="hover">
          {entityLabel}
        </Link>
        <Typography color="text.primary">{roleType}</Typography>
      </Breadcrumbs>

      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(canonicalEntityPath)}
          variant="outlined"
          size="small"
        >
          {t("common.back", "Back to entity")}
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h4" component="h1">
            {t("property.title", "Property: {{roleType}}", { roleType })}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            {t("property.subtitle", "For entity: {{entity}}", { entity: entityLabel })}
          </Typography>

          <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
            <Chip icon={consensus.icon} label={consensus.label} color={consensus.color} size="medium" />
            <Chip
              label={t("property.confidence", "Confidence: {{value}}%", {
                value: Math.round(explanation.confidence * 100),
              })}
              variant="outlined"
            />
            <Chip
              label={t("property.disagreement", "Disagreement: {{value}}%", {
                value: Math.round(explanation.disagreement * 100),
              })}
              variant="outlined"
              color={explanation.disagreement > 0.3 ? "warning" : "default"}
            />
          </Box>
        </Stack>
      </Paper>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            {t("property.conclusion", "Conclusion")}
          </Typography>

          {explanation.score !== null && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {t("property.score_label", "Computed Score")}
              </Typography>
              <Chip label={explanation.score.toFixed(3)} color={scoreColor} size="medium" />
            </Box>
          )}

          <Typography variant="body1" sx={{ fontStyle: "italic", color: "text.secondary" }}>
            {formatExplanationSummary(explanation.summary, t)}
          </Typography>
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
            {t("property.summary_disclaimer", "Generated summary. Use evidence below for auditability.")}
          </Typography>
        </CardContent>
      </Card>

      {limitations.length > 0 && (
        <Card>
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="h6">{t("property.limitations", "Known Limitations")}</Typography>
              <List dense>
                {limitations.map((item, index) => (
                  <ListItem key={index}>
                    <ListItemText primary={item} />
                  </ListItem>
                ))}
              </List>
            </Stack>
          </CardContent>
        </Card>
      )}

      {hasContradictions && contradictionDetail && (
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
                {t(
                  "property.contradictions_warning",
                  "Conflicting evidence is present and displayed explicitly.",
                )}
              </Alert>

              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <Chip
                  color="success"
                  variant="outlined"
                  label={t("property.supporting_sources", "Supporting: {{count}}", {
                    count: contradictionDetail.supporting_sources.length,
                  })}
                />
                <Chip
                  color="error"
                  variant="outlined"
                  label={t("property.contradicting_sources", "Contradicting: {{count}}", {
                    count: contradictionDetail.contradicting_sources.length,
                  })}
                />
                <Chip
                  variant="outlined"
                  label={t("property.disagreement_score", "Disagreement score: {{value}}", {
                    value: contradictionDetail.disagreement_score.toFixed(2),
                  })}
                />
              </Box>
            </Stack>
          </CardContent>
        </Card>
      )}

      <Divider />

      <Box>
        <Typography variant="h5" gutterBottom>
          {t("property.evidence", "Supporting Evidence")}
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          {t(
            "property.evidence_description",
            "Complete evidence chain supporting this conclusion.",
          )}
        </Typography>

        {explanation.source_chain.length > 0 ? (
          <EvidenceTrace sourceChain={explanation.source_chain} />
        ) : (
          <Alert severity="warning">{t("property.no_evidence", "No evidence chain available")}</Alert>
        )}
      </Box>

      <Box sx={{ display: "flex", justifyContent: "center" }}>
        <Button variant="outlined" onClick={() => navigate(entitySubpath(entity, `properties/${roleType}/evidence`))}>
          {t("property.view_all_evidence", "View All Related Evidence")}
        </Button>
      </Box>
    </Stack>
  );
}

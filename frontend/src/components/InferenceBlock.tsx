import { Link as RouterLink } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Link,
  Stack,
  Typography,
} from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { useTranslation } from "react-i18next";

import type { InferenceRead, RoleInference } from "../types/inference";
import type { RelationRead } from "../types/relation";
import {
  formatDirectionLabel,
  formatRelationClaim,
  formatRelationContext,
  normalizeRelationDirection,
} from "../utils/relationPresentation";

function getScoreInterpretation(score: number | null): {
  key: "supports" | "contradicts" | "mixed" | "none";
  color: "success" | "error" | "warning" | "default";
} {
  if (score === null) {
    return { key: "none", color: "default" };
  }
  if (score >= 0.3) {
    return { key: "supports", color: "success" };
  }
  if (score <= -0.3) {
    return { key: "contradicts", color: "error" };
  }
  return { key: "mixed", color: "warning" };
}

function ScoreBar({ score }: { score: number | null }) {
  const { t } = useTranslation();

  if (score === null) {
    return (
      <Typography variant="body2" color="text.secondary">
        {t("inference.no_score", "No computed score yet")}
      </Typography>
    );
  }

  const percentage = ((score + 1) / 2) * 100;
  const { color } = getScoreInterpretation(score);
  const progressColor = color === "default" ? "primary" : color;

  return (
    <Box sx={{ width: "100%" }}>
      <Stack direction="row" spacing={2} alignItems="center">
        <Box sx={{ flex: 1 }}>
          <LinearProgress
            variant="determinate"
            value={percentage}
            color={progressColor}
            sx={{ height: 8, borderRadius: 1 }}
          />
        </Box>
        <Typography
          variant="h6"
          sx={{
            minWidth: 60,
            textAlign: "right",
            color: `${color}.main`,
            fontWeight: "bold",
          }}
        >
          {score.toFixed(2)}
        </Typography>
      </Stack>
      <Stack direction="row" justifyContent="space-between" mt={1}>
        <Typography variant="caption" color="text.secondary">
          {t("inference.score_negative", "More contradicting evidence")}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t("inference.score_neutral", "Mixed or limited signal")}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t("inference.score_positive", "More supporting evidence")}
        </Typography>
      </Stack>
    </Box>
  );
}

function RelationDisplay({ relation, kind }: { relation: RelationRead; kind: string }) {
  const { t } = useTranslation();
  const direction = normalizeRelationDirection(relation.direction);
  const contextParts = formatRelationContext(relation);

  return (
    <Box sx={{ p: 1.5, bgcolor: "background.default", borderRadius: 1 }}>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" mb={0.75}>
        <Chip
          label={formatDirectionLabel(relation.direction)}
          size="small"
          color={
            direction === "supports"
              ? "success"
              : direction === "contradicts"
                ? "error"
                : "default"
          }
        />
        <Chip
          label={t("inference.evidence_confidence", {
            defaultValue: "Evidence confidence: {{value}}%",
            value: relation.confidence != null ? Math.round(relation.confidence * 100) : "N/A",
          })}
          size="small"
          variant="outlined"
        />
      </Stack>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {formatRelationClaim(relation, kind)}
      </Typography>
      {contextParts.length > 0 && (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
          {contextParts.join(" • ")}
        </Typography>
      )}
      <Link
        component={RouterLink}
        to={`/sources/${relation.source_id}`}
        variant="caption"
        sx={{ display: "inline-block", mt: 0.75 }}
      >
        {t("inference.open_source", "Open source evidence")}
      </Link>
    </Box>
  );
}

function InferenceLegend() {
  const { t } = useTranslation();

  return (
    <Alert severity="info" sx={{ mb: 2 }}>
      <Typography variant="body2">
        {t(
          "inference.legend_text",
          "Read these metrics together: score shows whether evidence leans supportive or contradictory, confidence shows how much evidence backs that reading, coverage counts how many relations were included, and disagreement highlights conflict between sources."
        )}
      </Typography>
    </Alert>
  );
}

function RoleInferenceCard({
  roleInference,
  entityId,
}: {
  roleInference: RoleInference;
  entityId: string;
}) {
  const { t } = useTranslation();
  const { role_type, score, coverage, confidence, disagreement } = roleInference;
  const interpretation = getScoreInterpretation(score);

  const interpretationText = {
    supports: t(
      "inference.role_supports",
      "The current evidence leans toward this role being supported for the entity."
    ),
    contradicts: t(
      "inference.role_contradicts",
      "The current evidence leans toward this role being contradicted for the entity."
    ),
    mixed: t(
      "inference.role_mixed",
      "The current evidence is mixed, weak, or too balanced to support a strong reading."
    ),
    none: t("inference.role_none", "No computed reading is available for this role yet."),
  }[interpretation.key];

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", sm: "flex-start" }}
          spacing={2}
          mb={2}
        >
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6">
              {t("inference.role_heading", {
                defaultValue: "{{role}} role",
                role: role_type,
              })}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {interpretationText}
            </Typography>
          </Box>
          <Button
            component={RouterLink}
            to={`/entities/${entityId}/properties/${role_type}`}
            size="small"
            startIcon={<HelpOutlineIcon />}
            variant="outlined"
          >
            {t("inference.explain", "View detail")}
          </Button>
        </Stack>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip
            label={t("inference.coverage_chip", {
              defaultValue: "{{n}} relation{{suffix}} reviewed",
              n: coverage.toFixed(0),
              suffix: coverage === 1 ? "" : "s",
            })}
            size="small"
            variant="outlined"
          />
          {score !== null && (
            <Chip
              label={t("inference.score_chip", {
                defaultValue: "Score {{value}}",
                value: score.toFixed(2),
              })}
              size="small"
              variant="outlined"
            />
          )}
          <Chip
            label={t("inference.confidence_chip", {
              defaultValue: "{{value}}% confidence",
              value: Math.round(confidence * 100),
            })}
            size="small"
            color={confidence > 0.7 ? "success" : confidence > 0.4 ? "warning" : "default"}
            variant="outlined"
          />
          <Chip
            label={t("inference.disagreement_chip", {
              defaultValue: "{{value}}% disagreement",
              value: Math.round(disagreement * 100),
            })}
            size="small"
            color={disagreement > 0.3 ? "warning" : "default"}
            variant="outlined"
          />
        </Stack>

        {score !== null && (
          <Box sx={{ mt: 2 }}>
            <ScoreBar score={score} />
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

export function InferenceBlock({
  inference,
}: {
  inference: InferenceRead | null;
  currentEntitySlug?: string;
}) {
  const { t } = useTranslation();

  if (!inference) {
    return null;
  }

  return (
    <Stack spacing={3}>
      {inference.role_inferences && inference.role_inferences.length > 0 && (
        <Box>
          <Typography variant="h5" gutterBottom>
            {t("inference.computed_reading_title", "Computed Reading of the Evidence")}
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            {t(
              "inference.computed_reading_description",
              "This section summarizes how the current evidence reads for each role. It is a computed interpretation of the evidence base, not an unquestionable conclusion."
            )}
          </Typography>
          <InferenceLegend />
          <Stack spacing={2}>
            {inference.role_inferences.map((roleInf) => (
              <RoleInferenceCard
                key={roleInf.role_type}
                roleInference={roleInf}
                entityId={inference.entity_id}
              />
            ))}
          </Stack>
        </Box>
      )}

      <Box>
        <Typography variant="h5" gutterBottom>
          {t("inference.source_evidence_title", "Source Evidence")}
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          {t(
            "inference.source_evidence_description",
            "These source-backed relations are the evidence the computed reading is built from. Use them to inspect the exact claims, their direction, and their context."
          )}
        </Typography>
        <Stack spacing={2}>
          {Object.entries(inference.relations_by_kind).map(([kind, relations]) => (
            <Card key={kind} variant="outlined">
              <CardContent>
                <Typography variant="h6">{kind}</Typography>

                <Stack spacing={1} mt={1}>
                  {relations.map((relation) => (
                    <RelationDisplay key={relation.id} relation={relation} kind={kind} />
                  ))}
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      </Box>
    </Stack>
  );
}

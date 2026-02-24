import { Link as RouterLink } from "react-router-dom";
import {
  Typography,
  Card,
  CardContent,
  Stack,
  Chip,
  Box,
  LinearProgress,
  Alert,
  Button,
  Link,
} from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { InferenceRead, RoleInference, EntityRoleInference } from "../types/inference";
import { RelationRead } from "../types/relation";

function ScoreBar({ score }: { score: number | null }) {
  if (score === null) {
    return <Typography variant="body2" color="text.secondary">No data</Typography>;
  }

  // Map score from [-1, 1] to [0, 100] for display
  const percentage = ((score + 1) / 2) * 100;

  // Color based on score
  const color = score > 0.3 ? "success" : score < -0.3 ? "error" : "warning";

  return (
    <Box sx={{ width: '100%' }}>
      <Stack direction="row" spacing={2} alignItems="center">
        <Box sx={{ flex: 1 }}>
          <LinearProgress
            variant="determinate"
            value={percentage}
            color={color}
            sx={{ height: 8, borderRadius: 1 }}
          />
        </Box>
        <Typography
          variant="h6"
          sx={{
            minWidth: 60,
            textAlign: 'right',
            color: `${color}.main`,
            fontWeight: 'bold'
          }}
        >
          {score.toFixed(2)}
        </Typography>
      </Stack>
    </Box>
  );
}

function RelationDisplay({ relation, kind }: { relation: RelationRead; kind: string }) {
  // Sort roles by role_type (subject first, then object, then others)
  const sortedRoles = [...relation.roles].sort((a, b) => {
    const order: Record<string, number> = { subject: 0, object: 1 };
    return (order[a.role_type] ?? 2) - (order[b.role_type] ?? 2);
  });

  // Find subject and object roles
  const subject = sortedRoles.find(r => r.role_type === "subject");
  const object = sortedRoles.find(r => r.role_type === "object");

  // Build natural language sentence
  let sentence = "";

  if (subject?.entity_slug && object?.entity_slug) {
    // Use natural language based on relation kind
    const kindLower = kind.toLowerCase();

    if (kindLower.includes("treat") || kindLower === "treats") {
      sentence = `${subject.entity_slug} treats ${object.entity_slug}`;
    } else if (kindLower.includes("biomarker")) {
      sentence = `${subject.entity_slug} is biomarker for ${object.entity_slug}`;
    } else if (kindLower.includes("affect") || kindLower.includes("population")) {
      sentence = `${subject.entity_slug} affects ${object.entity_slug}`;
    } else if (kindLower.includes("cause") || kindLower === "causes") {
      sentence = `${subject.entity_slug} causes ${object.entity_slug}`;
    } else if (kindLower.includes("correlate") || kindLower === "correlates") {
      sentence = `${subject.entity_slug} correlates with ${object.entity_slug}`;
    } else {
      // Default: just display as "subject kind object"
      sentence = `${subject.entity_slug} ${kind} ${object.entity_slug}`;
    }
  } else {
    // Fallback: display all roles with their types
    sentence = sortedRoles
      .map(r => `${r.entity_slug || r.entity_id} (${r.role_type})`)
      .join(" → ");
  }

  return (
    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
      <Chip
        label={relation.direction || "neutral"}
        size="small"
        color={
          relation.direction === "supports" ? "success" :
          relation.direction === "contradicts" ? "error" : "default"
        }
      />
      <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
        {subject?.entity_slug && (
          <Link
            component={RouterLink}
            to={`/entities/${subject.entity_slug}`}
            sx={{ fontWeight: 'bold', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
          >
            {subject.entity_slug}
          </Link>
        )}
        {subject?.entity_slug && object?.entity_slug && (
          <span style={{ marginLeft: 4, marginRight: 4 }}>
            {kind.toLowerCase().includes("treat") ? "treats" :
             kind.toLowerCase().includes("biomarker") ? "is biomarker for" :
             kind.toLowerCase().includes("affect") ? "affects" :
             kind.toLowerCase().includes("cause") ? "causes" :
             kind.toLowerCase().includes("correlate") ? "correlates with" :
             kind}
          </span>
        )}
        {object?.entity_slug && (
          <Link
            component={RouterLink}
            to={`/entities/${object.entity_slug}`}
            sx={{ fontWeight: 'bold', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
          >
            {object.entity_slug}
          </Link>
        )}
        {!subject?.entity_slug && !object?.entity_slug && (
          <span>{sentence}</span>
        )}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        confidence: {relation.confidence?.toFixed(2) || "N/A"}
      </Typography>
    </Stack>
  );
}

function EntityInferenceItem({
  entityInference,
}: {
  entityInference: EntityRoleInference;
}) {
  const { entity_slug, score, source_count, confidence, disagreement } = entityInference;

  return (
    <Box sx={{ mb: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
        <Link
          component={RouterLink}
          to={`/entities/${entity_slug}`}
          variant="body1"
          sx={{ fontWeight: 600, textDecoration: 'none', '&:hover': { textDecoration: 'underline' } }}
        >
          {entity_slug}
        </Link>
        <Stack direction="row" spacing={1}>
          <Chip
            label={`${source_count} sources`}
            size="small"
            variant="outlined"
          />
          <Chip
            label={`${(confidence * 100).toFixed(0)}% confidence`}
            size="small"
            color={confidence > 0.7 ? "success" : confidence > 0.4 ? "warning" : "default"}
            variant="outlined"
          />
        </Stack>
      </Stack>
      <ScoreBar score={score} />
      {disagreement > 0.3 && (
        <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
          {(disagreement * 100).toFixed(0)}% disagreement
        </Typography>
      )}
    </Box>
  );
}

function RoleInferenceCard({
  roleInference,
  entityId,
  currentEntitySlug
}: {
  roleInference: RoleInference;
  entityId: string;
  currentEntitySlug?: string;
}) {
  const { role_type, score, coverage, confidence, disagreement } = roleInference;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6">
              {role_type} role
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Coverage: {coverage.toFixed(0)} relations
              {score !== null && ` • Score: ${score.toFixed(2)}`}
              {` • Confidence: ${(confidence * 100).toFixed(0)}%`}
              {disagreement > 0 && ` • Disagreement: ${(disagreement * 100).toFixed(0)}%`}
            </Typography>
          </Box>
          <Button
            component={RouterLink}
            to={`/explain/${entityId}/${role_type}`}
            size="small"
            startIcon={<HelpOutlineIcon />}
            variant="outlined"
          >
            Explain
          </Button>
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

export function InferenceBlock({ inference, currentEntitySlug }: { inference: InferenceRead | null; currentEntitySlug?: string }) {
  if (!inference) {
    return null;
  }

  return (
    <Stack spacing={3}>
      {/* Computed Inference Scores */}
      {inference.role_inferences && inference.role_inferences.length > 0 && (
        <Box>
          <Typography variant="h5" gutterBottom>
            Computed Inference
          </Typography>
          <Stack spacing={2}>
            {inference.role_inferences.map((roleInf) => (
              <RoleInferenceCard
                key={roleInf.role_type}
                roleInference={roleInf}
                entityId={inference.entity_id}
                currentEntitySlug={currentEntitySlug}
              />
            ))}
          </Stack>
        </Box>
      )}

      {/* Source Relations (grouped by kind) */}
      <Box>
        <Typography variant="h5" gutterBottom>
          Source Evidence
        </Typography>
        <Stack spacing={2}>
          {Object.entries(inference.relations_by_kind).map(
            ([kind, relations]) => (
              <Card key={kind} variant="outlined">
                <CardContent>
                  <Typography variant="h6">{kind}</Typography>

                  <Stack spacing={1} mt={1}>
                    {relations.map((r) => (
                      <RelationDisplay key={r.id} relation={r} kind={kind} />
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            )
          )}
        </Stack>
      </Box>
    </Stack>
  );
}

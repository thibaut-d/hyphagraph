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
} from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { InferenceRead, RoleInference } from "../types/inference";

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

function RoleInferenceCard({
  roleInference,
  entityId
}: {
  roleInference: RoleInference;
  entityId: string;
}) {
  const { role_type, score, coverage, confidence, disagreement } = roleInference;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6">
            {role_type}
          </Typography>
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

        <Stack spacing={2}>
          {/* Main inference score */}
          <Box>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              Inference Score
            </Typography>
            <ScoreBar score={score} />
          </Box>

          {/* Metadata */}
          <Stack direction="row" spacing={2} flexWrap="wrap">
            <Chip
              label={`Coverage: ${coverage.toFixed(1)}`}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`Confidence: ${(confidence * 100).toFixed(0)}%`}
              size="small"
              color={confidence > 0.7 ? "success" : confidence > 0.4 ? "warning" : "default"}
              variant="outlined"
            />
            {disagreement > 0.3 && (
              <Chip
                label={`Disagreement: ${(disagreement * 100).toFixed(0)}%`}
                size="small"
                color="error"
                variant="outlined"
              />
            )}
          </Stack>

          {/* Warning for contradictory evidence */}
          {disagreement > 0.5 && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              High disagreement detected - sources contradict each other
            </Alert>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

export function InferenceBlock({ inference }: { inference: InferenceRead | null }) {
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
                      <Stack
                        key={r.id}
                        direction="row"
                        spacing={1}
                        alignItems="center"
                      >
                        <Chip label={r.direction} size="small" />
                        <Typography variant="body2">
                          confidence: {r.confidence}
                        </Typography>
                      </Stack>
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

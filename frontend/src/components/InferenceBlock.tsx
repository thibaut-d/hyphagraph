import {
  Typography,
  Card,
  CardContent,
  Stack,
  Chip,
} from "@mui/material";
import { InferenceRead } from "../types/inference";

export function InferenceBlock({ inference }: { inference: InferenceRead }) {
  return (
    <Stack spacing={2}>
      {Object.entries(inference.relations_by_kind).map(
        ([kind, relations]) => (
          <Card key={kind}>
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
  );
}
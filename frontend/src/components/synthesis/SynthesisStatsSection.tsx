import { useTranslation } from "react-i18next";
import {
  Card,
  CardContent,
  Grid,
  LinearProgress,
  Typography,
} from "@mui/material";

interface SynthesisStatsSectionProps {
  totalRelations: number;
  uniqueSourcesCount: number;
  averageConfidence: number;
  relationTypeCount: number;
}

export function SynthesisStatsSection({
  totalRelations,
  uniqueSourcesCount,
  averageConfidence,
  relationTypeCount,
}: SynthesisStatsSectionProps) {
  const { t } = useTranslation();

  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, sm: 6, md: 3 }}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              {t("synthesis.stats.relations", "Total Relations")}
            </Typography>
            <Typography variant="h4">{totalRelations}</Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, sm: 6, md: 3 }}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              {t("synthesis.stats.sources", "Unique Sources")}
            </Typography>
            <Typography variant="h4">{uniqueSourcesCount}</Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, sm: 6, md: 3 }}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              {t("synthesis.stats.confidence", "Avg. Confidence")}
            </Typography>
            <Typography variant="h4">{Math.round(averageConfidence * 100)}%</Typography>
            <LinearProgress
              variant="determinate"
              value={averageConfidence * 100}
              sx={{ mt: 1 }}
            />
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, sm: 6, md: 3 }}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              {t("synthesis.stats.kinds", "Relation Types")}
            </Typography>
            <Typography variant="h4">{relationTypeCount}</Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

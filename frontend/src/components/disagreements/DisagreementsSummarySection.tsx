import { useTranslation } from "react-i18next";
import { Card, CardContent, Grid, Typography } from "@mui/material";

interface DisagreementsSummarySectionProps {
  groupCount: number;
  contradictionCount: number;
}

export function DisagreementsSummarySection({
  groupCount,
  contradictionCount,
}: DisagreementsSummarySectionProps) {
  const { t } = useTranslation();

  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, sm: 6 }}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              {t("disagreements.stats.types", "Conflicting Relation Types")}
            </Typography>
            <Typography variant="h4">{groupCount}</Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, sm: 6 }}>
        <Card>
          <CardContent>
            <Typography color="text.secondary" gutterBottom variant="body2">
              {t("disagreements.stats.total", "Total Contradictions")}
            </Typography>
            <Typography variant="h4" color="error">
              {contradictionCount}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

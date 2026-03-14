import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import InfoIcon from "@mui/icons-material/Info";

interface SynthesisFooterSectionProps {
  contradictionCount: number;
  relationTypeCount: number;
  onViewDisagreements: () => void;
  onBackToDetail: () => void;
}

export function SynthesisFooterSection({
  contradictionCount,
  relationTypeCount,
  onViewDisagreements,
  onBackToDetail,
}: SynthesisFooterSectionProps) {
  const { t } = useTranslation();

  return (
    <>
      {relationTypeCount < 3 && (
        <Card sx={{ borderColor: "warning.main", borderWidth: 1, borderStyle: "dashed" }}>
          <CardContent>
            <Stack spacing={2}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <InfoIcon color="warning" />
                <Typography variant="h6" color="warning.main">
                  {t("synthesis.gaps.title", "Knowledge Gaps Detected")}
                </Typography>
              </Box>
              <Typography variant="body2">
                {t(
                  "synthesis.gaps.description",
                  "This entity has limited relation types. Consider adding more evidence or relations to improve knowledge coverage."
                )}
              </Typography>
            </Stack>
          </CardContent>
        </Card>
      )}

      <Divider />
      <Box sx={{ display: "flex", gap: 2, justifyContent: "center", flexWrap: "wrap" }}>
        {contradictionCount > 0 && (
          <Button variant="contained" color="error" onClick={onViewDisagreements}>
            {t("synthesis.view_disagreements", "View Disagreements ({{count}})", {
              count: contradictionCount,
            })}
          </Button>
        )}
        <Button variant="outlined" onClick={onBackToDetail}>
          {t("synthesis.back_to_detail", "Back to Entity Detail")}
        </Button>
      </Box>
    </>
  );
}

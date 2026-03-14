import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import InfoIcon from "@mui/icons-material/Info";

interface DisagreementsFooterSectionProps {
  onViewSynthesis: () => void;
  onBackToDetail: () => void;
}

export function DisagreementsFooterSection({
  onViewSynthesis,
  onBackToDetail,
}: DisagreementsFooterSectionProps) {
  const { t } = useTranslation();

  return (
    <>
      <Card>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
            <InfoIcon color="primary" />
            <Stack spacing={1}>
              <Typography variant="h6">
                {t("disagreements.guidance.title", "How to Interpret Disagreements")}
              </Typography>
              <Box sx={{ color: "text.secondary" }}>
                {t(
                  "disagreements.guidance.text",
                  "• Contradictions are normal in science - they indicate evolving knowledge.\n" +
                    "• Check source quality and publication dates - newer studies may supersede older ones.\n" +
                    "• Look for methodological differences - studies with different designs may reach different conclusions.\n" +
                    "• Consult domain experts when making critical decisions based on contradictory evidence."
                )
                  .split("\n")
                  .map((line, index) => (
                    <Typography key={index} variant="body2" component="div">
                      {line}
                    </Typography>
                  ))}
              </Box>
            </Stack>
          </Box>
        </CardContent>
      </Card>

      <Divider />
      <Box sx={{ display: "flex", gap: 2, justifyContent: "center", flexWrap: "wrap" }}>
        <Button variant="outlined" onClick={onViewSynthesis}>
          {t("disagreements.view_synthesis", "View Full Synthesis")}
        </Button>
        <Button variant="outlined" onClick={onBackToDetail}>
          {t("disagreements.back_to_detail", "Back to Entity Detail")}
        </Button>
      </Box>
    </>
  );
}

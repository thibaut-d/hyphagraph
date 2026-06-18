import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import UpdateIcon from "@mui/icons-material/Update";

import { generateEntityAISynthesis, ScopeFilter } from "../../api/inferences";
import { useNotification } from "../../notifications/NotificationContext";
import type { EntityRead } from "../../types/entity";
import type { EntityAISynthesisRead } from "../../types/inference";

interface EntityAISynthesisBlockProps {
  entity: EntityRead;
  scopeFilter: ScopeFilter;
  hasInference: boolean;
}

export function EntityAISynthesisBlock({
  entity,
  scopeFilter,
  hasInference,
}: EntityAISynthesisBlockProps) {
  const { t, i18n } = useTranslation();
  const { showError } = useNotification();
  const [synthesis, setSynthesis] = useState<EntityAISynthesisRead | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const result = await generateEntityAISynthesis(entity.id, {
        user_language: i18n.language || "en",
        scope_filter: Object.keys(scopeFilter).length > 0 ? scopeFilter : null,
      });
      setSynthesis(result);
    } catch (error) {
      showError(error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Paper sx={{ p: { xs: 2, sm: 3 } }}>
      <Stack spacing={2}>
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            justifyContent: "space-between",
            alignItems: { xs: "flex-start", sm: "center" },
            gap: 1.5,
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Typography variant="h5">
              {t("entity_ai_synthesis.title", "AI synthesis")}
            </Typography>
            <Chip
              icon={<AutoAwesomeIcon />}
              label={t("entity_ai_synthesis.advisory_chip", "AI-generated")}
              size="small"
              color="secondary"
              variant="outlined"
            />
            {synthesis && (
              <Chip
                label={t("entity_ai_synthesis.model_chip", {
                  defaultValue: "Model: {{model}}",
                  model: synthesis.generated_with_llm,
                })}
                size="small"
                variant="outlined"
              />
            )}
          </Stack>

          <Button
            variant={synthesis ? "outlined" : "contained"}
            startIcon={
              isGenerating
                ? <CircularProgress color="inherit" size={16} />
                : synthesis
                  ? <UpdateIcon />
                  : <AutoAwesomeIcon />
            }
            onClick={handleGenerate}
            disabled={isGenerating || !hasInference}
          >
            {isGenerating
              ? t("entity_ai_synthesis.generating", "Generating...")
              : synthesis
                ? t("entity_ai_synthesis.update", "Update AI synthesis")
                : t("entity_ai_synthesis.generate", "Generate AI synthesis")}
          </Button>
        </Box>

        <Alert severity="info">
          {t(
            "entity_ai_synthesis.advisory_notice",
            "This text is generated on demand from computed graph relationships. It is not authoritative and does not replace the evidence below."
          )}
        </Alert>

        {!hasInference && (
          <Typography color="text.secondary">
            {t(
              "entity_ai_synthesis.no_inference",
              "No computed relationships are available yet, so an AI synthesis cannot be generated."
            )}
          </Typography>
        )}

        {synthesis && (
          <Stack spacing={2}>
            <Typography>{synthesis.synthesis}</Typography>

            {synthesis.key_points.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  {t("entity_ai_synthesis.key_points", "Key points")}
                </Typography>
                <Stack component="ul" spacing={0.5} sx={{ pl: 3, my: 0 }}>
                  {synthesis.key_points.map((point) => (
                    <Typography component="li" key={point} variant="body2">
                      {point}
                    </Typography>
                  ))}
                </Stack>
              </Box>
            )}

            {synthesis.limitations.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  {t("entity_ai_synthesis.limitations", "Limitations")}
                </Typography>
                <Stack component="ul" spacing={0.5} sx={{ pl: 3, my: 0 }}>
                  {synthesis.limitations.map((limitation) => (
                    <Typography component="li" key={limitation} variant="body2">
                      {limitation}
                    </Typography>
                  ))}
                </Stack>
              </Box>
            )}

            <Alert severity="warning">
              {synthesis.evidence_note}
              {synthesis.general_knowledge_note && (
                <>
                  {" "}
                  {synthesis.general_knowledge_note}
                </>
              )}
            </Alert>

            <Typography variant="caption" color="text.secondary">
              {t("entity_ai_synthesis.evidence_counts", {
                defaultValue:
                  "Generated from {{relations}} relation(s) across {{sources}} source(s).",
                relations: synthesis.source_relation_count,
                sources: synthesis.source_count,
              })}
            </Typography>
          </Stack>
        )}
      </Stack>
    </Paper>
  );
}

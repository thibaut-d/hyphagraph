import { useEffect, useState } from "react";
import { useParams, Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Typography,
  Paper,
  Stack,
  CircularProgress,
  Button,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";

import { getEntity } from "../api/entities";
import { getInferenceForEntity } from "../api/inferences";

import { EntityRead } from "../types/entity";
import { InferenceRead } from "../types/inference";

import { InferenceBlock } from "../components/InferenceBlock";
import { resolveLabel } from "../utils/i18nLabel";

export function EntityDetailView() {
  const { id } = useParams<{ id: string }>();
  const { t, i18n } = useTranslation();

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [inference, setInference] = useState<InferenceRead | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;

    setLoading(true);

    Promise.all([
      getEntity(id),
      getInferenceForEntity(id),
    ])
      .then(([entityRes, inferenceRes]) => {
        setEntity(entityRes);
        setInference(inferenceRes);
      })
      .finally(() => setLoading(false));
  }, [id]);

  // Loading state
  if (loading) {
    return (
      <Stack alignItems="center" mt={4}>
        <CircularProgress />
      </Stack>
    );
  }

  // Not found
  if (!entity) {
    return (
      <Typography color="error">
        {t("common.not_found", "Not found")}
      </Typography>
    );
  }

  const label = resolveLabel(
    entity.label,
    entity.label_i18n,
    i18n.language,
  );

  return (
    <Stack spacing={3}>
      {/* Header */}
      <Paper sx={{ p: 3 }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
        >
          <div>
            <Typography variant="h4">{label}</Typography>
            <Typography variant="subtitle2" color="text.secondary">
              {entity.kind}
            </Typography>
          </div>

          <Button
            component={RouterLink}
            to={`/relations/new?entity_id=${entity.id}`}
            variant="contained"
            startIcon={<AddIcon />}
          >
            {t("relation.create", "Create relation")}
          </Button>
        </Stack>
      </Paper>

      {/* Inference */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          {t("entity.inference", "Related assertions")}
        </Typography>

        {inference ? (
          <InferenceBlock inference={inference} />
        ) : (
          <Typography color="text.secondary">
            {t("common.no_data", "No data")}
          </Typography>
        )}
      </Paper>
    </Stack>
  );
}
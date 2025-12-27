import { useEffect, useState } from "react";
import { useParams, Link as RouterLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Typography,
  Paper,
  Stack,
  CircularProgress,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  IconButton,
  Box,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";

import { getEntity, deleteEntity } from "../api/entities";
import { getInferenceForEntity } from "../api/inferences";

import { EntityRead } from "../types/entity";
import { InferenceRead } from "../types/inference";

import { InferenceBlock } from "../components/InferenceBlock";
import { resolveLabel } from "../utils/i18nLabel";

export function EntityDetailView() {
  const { id } = useParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [inference, setInference] = useState<InferenceRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

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

  const handleDelete = async () => {
    if (!id) return;

    setDeleting(true);
    try {
      await deleteEntity(id);
      navigate("/entities");
    } catch (error) {
      console.error("Failed to delete entity:", error);
      setDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

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

          <Box sx={{ display: "flex", gap: 1 }}>
            <IconButton
              component={RouterLink}
              to={`/entities/${entity.id}/edit`}
              color="primary"
              title={t("common.edit", "Edit")}
            >
              <EditIcon />
            </IconButton>
            <IconButton
              onClick={() => setDeleteDialogOpen(true)}
              color="error"
              title={t("common.delete", "Delete")}
            >
              <DeleteIcon />
            </IconButton>
            <Button
              component={RouterLink}
              to={`/relations/new?entity_id=${entity.id}`}
              variant="contained"
              startIcon={<AddIcon />}
            >
              {t("relation.create", "Create relation")}
            </Button>
          </Box>
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

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !deleting && setDeleteDialogOpen(false)}
      >
        <DialogTitle>
          {t("entity.delete_confirm_title", "Delete Entity")}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t(
              "entity.delete_confirm_message",
              "Are you sure you want to delete this entity? This action cannot be undone."
            )}
          </DialogContentText>
          <Typography variant="body2" sx={{ mt: 2, fontWeight: 600 }}>
            {label}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button onClick={handleDelete} color="error" disabled={deleting}>
            {deleting
              ? t("common.deleting", "Deleting...")
              : t("common.delete", "Delete")}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
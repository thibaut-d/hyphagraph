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
  TextField,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FilterListIcon from "@mui/icons-material/FilterList";
import CloseIcon from "@mui/icons-material/Close";

import { getEntity, deleteEntity } from "../api/entities";
import { getInferenceForEntity, ScopeFilter } from "../api/inferences";

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

  // Scope filter state
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>({});
  const [newFilterKey, setNewFilterKey] = useState("");
  const [newFilterValue, setNewFilterValue] = useState("");

  const loadInference = async (filter: ScopeFilter) => {
    if (!id) return;

    try {
      const inferenceRes = await getInferenceForEntity(id, filter);
      setInference(inferenceRes);
    } catch (error) {
      console.error("Failed to load inference:", error);
    }
  };

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

  const handleAddFilter = () => {
    if (!newFilterKey.trim() || !newFilterValue.trim()) return;

    const updatedFilter = {
      ...scopeFilter,
      [newFilterKey.trim()]: newFilterValue.trim(),
    };

    setScopeFilter(updatedFilter);
    setNewFilterKey("");
    setNewFilterValue("");

    loadInference(updatedFilter);
  };

  const handleRemoveFilter = (key: string) => {
    const updatedFilter = { ...scopeFilter };
    delete updatedFilter[key];

    setScopeFilter(updatedFilter);
    loadInference(updatedFilter);
  };

  const handleClearFilters = () => {
    setScopeFilter({});
    loadInference({});
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
        <Stack spacing={2}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Typography variant="h5">
              {t("entity.inference", "Related assertions")}
            </Typography>

            {Object.keys(scopeFilter).length > 0 && (
              <Button
                size="small"
                onClick={handleClearFilters}
                startIcon={<CloseIcon />}
              >
                Clear Filters
              </Button>
            )}
          </Box>

          {/* Scope Filter Controls */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Stack direction="row" spacing={1} alignItems="center">
                <FilterListIcon fontSize="small" />
                <Typography>
                  Scope Filter
                  {Object.keys(scopeFilter).length > 0 &&
                    ` (${Object.keys(scopeFilter).length} active)`}
                </Typography>
              </Stack>
            </AccordionSummary>
            <AccordionDetails>
              <Stack spacing={2}>
                {/* Active Filters */}
                {Object.keys(scopeFilter).length > 0 && (
                  <Box>
                    <Typography variant="caption" color="text.secondary" gutterBottom>
                      Active Filters:
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
                      {Object.entries(scopeFilter).map(([key, value]) => (
                        <Chip
                          key={key}
                          label={`${key}: ${value}`}
                          onDelete={() => handleRemoveFilter(key)}
                          size="small"
                          color="primary"
                        />
                      ))}
                    </Stack>
                  </Box>
                )}

                {/* Add Filter Form */}
                <Box>
                  <Typography variant="caption" color="text.secondary" gutterBottom>
                    Add Filter:
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                    <TextField
                      size="small"
                      label="Attribute"
                      value={newFilterKey}
                      onChange={(e) => setNewFilterKey(e.target.value)}
                      placeholder="e.g., population"
                      sx={{ flex: 1 }}
                    />
                    <TextField
                      size="small"
                      label="Value"
                      value={newFilterValue}
                      onChange={(e) => setNewFilterValue(e.target.value)}
                      placeholder="e.g., adults"
                      sx={{ flex: 1 }}
                      onKeyPress={(e) => {
                        if (e.key === "Enter") {
                          handleAddFilter();
                        }
                      }}
                    />
                    <Button
                      variant="contained"
                      onClick={handleAddFilter}
                      disabled={!newFilterKey.trim() || !newFilterValue.trim()}
                    >
                      Add
                    </Button>
                  </Stack>
                </Box>

                {/* Help Text */}
                <Typography variant="caption" color="text.secondary">
                  Filter inferences by scope attributes like population, condition, dosage, etc.
                  Only relations matching ALL filter criteria will be included in the inference.
                </Typography>
              </Stack>
            </AccordionDetails>
          </Accordion>

          {/* Inference Display */}
          {inference ? (
            <InferenceBlock inference={inference} />
          ) : (
            <Typography color="text.secondary">
              {t("common.no_data", "No data")}
            </Typography>
          )}
        </Stack>
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

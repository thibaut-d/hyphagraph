import { useEffect, useState, useMemo } from "react";
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
  Box,
  TextField,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Badge,
  Alert,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FilterListIcon from "@mui/icons-material/FilterList";
import CloseIcon from "@mui/icons-material/Close";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SearchIcon from "@mui/icons-material/Search";

import { getEntity, deleteEntity } from "../api/entities";
import { getInferenceForEntity, ScopeFilter } from "../api/inferences";
import { getSource } from "../api/sources";

import { EntityRead } from "../types/entity";
import { InferenceRead } from "../types/inference";
import { SourceRead } from "../types/source";
import { RelationRead } from "../types/relation";

import { InferenceBlock } from "../components/InferenceBlock";
import { EntityTermsDisplay } from "../components/EntityTermsDisplay";
import { FilterDrawer, EntityDetailFilters, EntityDetailFilterValues } from "../components/filters";
import { useFilterDrawer } from "../hooks/useFilterDrawer";

export function EntityDetailView() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [inference, setInference] = useState<InferenceRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Source data for filtering
  const [sources, setSources] = useState<Record<string, SourceRead>>({});
  const [loadingSources, setLoadingSources] = useState(false);

  // Scope filter state (existing population/condition filtering)
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>({});
  const [newFilterKey, setNewFilterKey] = useState("");
  const [newFilterValue, setNewFilterValue] = useState("");

  // Evidence filter drawer state (new UX.md Section 5.3 filtering)
  const {
    isOpen: filterDrawerOpen,
    openDrawer: openFilterDrawer,
    closeDrawer: closeFilterDrawer,
    filters: evidenceFilters,
    setFilter: setEvidenceFilter,
    clearAllFilters: clearEvidenceFilters,
    activeFilterCount: evidenceFilterCount,
  } = useFilterDrawer();

  const loadInference = async (filter: ScopeFilter) => {
    if (!id) return;

    try {
      const inferenceRes = await getInferenceForEntity(id, filter);
      setInference(inferenceRes);

      // Extract unique source IDs from relations
      const sourceIds = new Set<string>();
      Object.values(inferenceRes.relations_by_kind).forEach((relations) => {
        relations.forEach((rel) => {
          sourceIds.add(rel.source_id);
        });
      });

      // Fetch all source data for filtering
      if (sourceIds.size > 0) {
        setLoadingSources(true);
        const sourcePromises = Array.from(sourceIds).map(async (sourceId) => {
          try {
            return await getSource(sourceId);
          } catch (error) {
            console.error(`Failed to load source ${sourceId}:`, error);
            return null;
          }
        });

        const sourcesData = await Promise.all(sourcePromises);
        const sourcesMap: Record<string, SourceRead> = {};
        sourcesData.forEach((source) => {
          if (source) {
            sourcesMap[source.id] = source;
          }
        });
        setSources(sourcesMap);
        setLoadingSources(false);
      }
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
      .then(async ([entityRes, inferenceRes]) => {
        setEntity(entityRes);
        setInference(inferenceRes);

        // Extract unique source IDs from relations
        if (!inferenceRes) return;

        const sourceIds = new Set<string>();
        Object.values(inferenceRes.relations_by_kind).forEach((relations) => {
          relations.forEach((rel) => {
            sourceIds.add(rel.source_id);
          });
        });

        // Fetch all source data for filtering
        if (sourceIds.size > 0) {
          setLoadingSources(true);
          const sourcePromises = Array.from(sourceIds).map(async (sourceId) => {
            try {
              return await getSource(sourceId);
            } catch (error) {
              console.error(`Failed to load source ${sourceId}:`, error);
              return null;
            }
          });

          const sourcesData = await Promise.all(sourcePromises);
          const sourcesMap: Record<string, SourceRead> = {};
          sourcesData.forEach((source) => {
            if (source) {
              sourcesMap[source.id] = source;
            }
          });
          setSources(sourcesMap);
          setLoadingSources(false);
        }
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

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true);
  };

  // Apply evidence filters to inference data (client-side)
  const filteredInference = useMemo((): InferenceRead | null => {
    if (!inference || evidenceFilterCount === 0) {
      return inference;
    }

    const filters = evidenceFilters as EntityDetailFilterValues;

    // Filter relations based on evidence filters
    const filteredRelationsByKind: Record<string, RelationRead[]> = {};
    let totalFilteredOut = 0;

    Object.entries(inference.relations_by_kind).forEach(([kind, relations]) => {
      const filtered = relations.filter((relation) => {
        const source = sources[relation.source_id];
        if (!source) return true; // Keep if source not loaded yet

        // Filter by direction
        if (filters.directions && filters.directions.length > 0) {
          if (!relation.direction || !filters.directions.includes(relation.direction)) {
            totalFilteredOut++;
            return false;
          }
        }

        // Filter by source kind (study type)
        if (filters.kinds && filters.kinds.length > 0) {
          if (!filters.kinds.includes(source.kind)) {
            totalFilteredOut++;
            return false;
          }
        }

        // Filter by year range
        if (filters.yearRange) {
          const [minYear, maxYear] = filters.yearRange;
          if (source.year < minYear || source.year > maxYear) {
            totalFilteredOut++;
            return false;
          }
        }

        // Filter by minimum trust level
        if (filters.minTrustLevel !== undefined && filters.minTrustLevel > 0) {
          if (source.trust_level < filters.minTrustLevel) {
            totalFilteredOut++;
            return false;
          }
        }

        return true;
      });

      if (filtered.length > 0) {
        filteredRelationsByKind[kind] = filtered;
      }
    });

    return {
      ...inference,
      relations_by_kind: filteredRelationsByKind,
    };
  }, [inference, evidenceFilters, evidenceFilterCount, sources]);

  // Count total relations before and after filtering
  const totalRelationsCount = useMemo(() => {
    if (!inference) return 0;
    return Object.values(inference.relations_by_kind).reduce(
      (sum, relations) => sum + relations.length,
      0
    );
  }, [inference]);

  const filteredRelationsCount = useMemo(() => {
    if (!filteredInference) return 0;
    return Object.values(filteredInference.relations_by_kind).reduce(
      (sum, relations) => sum + relations.length,
      0
    );
  }, [filteredInference]);

  const hiddenRelationsCount = totalRelationsCount - filteredRelationsCount;

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

  const sourcesArray = Object.values(sources);

  return (
    <Stack spacing={3}>
      {/* Header */}
      <Paper sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack spacing={2}>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button
              component={RouterLink}
              to="/entities"
              startIcon={<ArrowBackIcon />}
              size="small"
            >
              {t("common.back", "Back")}
            </Button>
          </Box>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ xs: "flex-start", sm: "center" }}
            spacing={2}
          >
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h4" sx={{ fontSize: { xs: '1.75rem', sm: '2.125rem' } }}>
                {entity.slug}
              </Typography>
              <Typography variant="subtitle2" color="text.secondary">
                {entity.summary?.en || entity.kind}
              </Typography>

              {/* Alternative Names/Aliases */}
              <Box sx={{ mt: 2 }}>
                <EntityTermsDisplay entityId={entity.id} />
              </Box>
            </Box>

            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1}
              sx={{ width: { xs: '100%', sm: 'auto' } }}
            >
              <Button
                component={RouterLink}
                to={`/sources/smart-discovery?entity=${entity.slug}`}
                variant="contained"
                color="secondary"
                startIcon={<SearchIcon />}
                size="small"
                fullWidth={{ xs: true, sm: false }}
              >
                {t("entity.discover_sources", "Discover Sources")}
              </Button>
              <Button
                component={RouterLink}
                to={`/entities/${entity.id}/edit`}
                color="primary"
                startIcon={<EditIcon />}
                size="small"
                fullWidth={{ xs: true, sm: false }}
              >
                {t("common.edit", "Edit")}
              </Button>
              <Button
                onClick={handleDeleteClick}
                color="error"
                startIcon={<DeleteIcon />}
                size="small"
                fullWidth={{ xs: true, sm: false }}
              >
                {t("common.delete", "Delete")}
              </Button>
              <Button
                component={RouterLink}
                to={`/relations/new?entity_id=${entity.id}`}
                variant="outlined"
                startIcon={<AddIcon />}
                size="small"
                fullWidth={{ xs: true, sm: false }}
              >
                {t("relation.create", "Create relation")}
              </Button>
            </Stack>
          </Stack>
        </Stack>
      </Paper>

      {/* Inference */}
      <Paper sx={{ p: { xs: 2, sm: 3 } }}>
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

            <Stack direction="row" spacing={2}>
              {/* Evidence Filter Button */}
              <Badge badgeContent={evidenceFilterCount} color="primary">
                <Button
                  variant="outlined"
                  startIcon={<FilterListIcon />}
                  onClick={openFilterDrawer}
                  disabled={loadingSources}
                >
                  {t("filters.evidence", "Filter Evidence")}
                </Button>
              </Badge>

              {Object.keys(scopeFilter).length > 0 && (
                <Button
                  size="small"
                  onClick={handleClearFilters}
                  startIcon={<CloseIcon />}
                >
                  Clear Scope Filters
                </Button>
              )}
            </Stack>
          </Box>

          {/* Warning when evidence is hidden by filters */}
          {evidenceFilterCount > 0 && hiddenRelationsCount > 0 && (
            <Alert severity="warning">
              {t(
                "filters.evidence_hidden_warning",
                "{{count}} relation(s) hidden by evidence filters. These are excluded from the view but do not affect computed scores.",
                { count: hiddenRelationsCount }
              )}
            </Alert>
          )}

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
          {filteredInference ? (
            <InferenceBlock inference={filteredInference} />
          ) : (
            <Typography color="text.secondary">
              {t("common.no_data", "No data")}
            </Typography>
          )}
        </Stack>
      </Paper>

      {/* Evidence Filter Drawer */}
      <FilterDrawer
        open={filterDrawerOpen}
        onClose={closeFilterDrawer}
        title={t("filters.evidence", "Filter Evidence")}
        activeFilterCount={evidenceFilterCount}
        onClearAll={clearEvidenceFilters}
      >
        <EntityDetailFilters
          filters={evidenceFilters as EntityDetailFilterValues}
          onFilterChange={setEvidenceFilter}
          sources={sourcesArray}
        />
      </FilterDrawer>

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
            {entity.slug}
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

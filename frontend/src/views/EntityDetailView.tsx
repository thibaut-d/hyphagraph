import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Alert, Typography, Stack, CircularProgress } from "@mui/material";

import { EntityDetailFilterValues, FilterDrawer, EntityDetailFilters } from "../components/filters";
import { EntityDetailHeader } from "../components/entity/EntityDetailHeader";
import { EntityDeleteDialog } from "../components/entity/EntityDeleteDialog";
import { ScopeFilterPanel } from "../components/entity/ScopeFilterPanel";
import { InferenceSection } from "../components/entity/InferenceSection";

import { useEntityData } from "../hooks/useEntityData";
import { useEntityInference } from "../hooks/useEntityInference";
import { useScopeFilter } from "../hooks/useScopeFilter";
import { useInferenceFiltering } from "../hooks/useInferenceFiltering";
import { useEntityDeletion } from "../hooks/useEntityDeletion";
import { useFilterDrawer } from "../hooks/useFilterDrawer";

export function EntityDetailView() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  // Custom hooks
  const { entity, loading, error } = useEntityData(id);
  const { inference, sources, loadingSources, error: inferenceError, loadInference } = useEntityInference(id);
  const {
    scopeFilter,
    newFilterKey,
    newFilterValue,
    setNewFilterKey,
    setNewFilterValue,
    addFilter,
    removeFilter,
    clearFilters,
  } = useScopeFilter();
  const {
    isDialogOpen: deleteDialogOpen,
    isDeleting: deleting,
    openDialog: openDeleteDialog,
    closeDialog: closeDeleteDialog,
    confirmDelete,
  } = useEntityDeletion();
  const {
    isOpen: filterDrawerOpen,
    openDrawer: openFilterDrawer,
    closeDrawer: closeFilterDrawer,
    filters: evidenceFilters,
    setFilter: setEvidenceFilter,
    clearAllFilters: clearEvidenceFilters,
    activeFilterCount: evidenceFilterCount,
  } = useFilterDrawer();

  // Use inference filtering hook
  const { filteredInference, hiddenRelationsCount } = useInferenceFiltering(
    inference,
    evidenceFilters as EntityDetailFilterValues,
    sources,
    evidenceFilterCount
  );

  // Handler functions
  const handleDeleteConfirm = () => {
    if (!id) return;
    confirmDelete(id, () => navigate("/entities"));
  };

  const handleAddFilter = () => {
    addFilter(newFilterKey, newFilterValue, loadInference);
  };

  const handleRemoveFilter = (key: string) => {
    removeFilter(key, loadInference);
  };

  const handleClearFilters = () => {
    clearFilters(loadInference);
  };

  // Loading state
  if (loading) {
    return (
      <Stack alignItems="center" mt={4}>
        <CircularProgress />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert severity="error">
        {error.message || t("common.error", "An error occurred")}
      </Alert>
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
      <EntityDetailHeader entity={entity} onDeleteClick={openDeleteDialog} />

      {/* Inference */}
      {inferenceError && (
        <Alert severity="error">
          {inferenceError.message || t("common.error", "An error occurred")}
        </Alert>
      )}

      <InferenceSection
        entity={entity}
        inference={inference}
        filteredInference={filteredInference}
        scopeFilter={scopeFilter}
        evidenceFilterCount={evidenceFilterCount}
        hiddenRelationsCount={hiddenRelationsCount}
        loadingSources={loadingSources}
        onOpenEvidenceFilter={openFilterDrawer}
        onClearScopeFilters={handleClearFilters}
        scopeFilterPanel={
          <ScopeFilterPanel
            scopeFilter={scopeFilter}
            newFilterKey={newFilterKey}
            newFilterValue={newFilterValue}
            onKeyChange={setNewFilterKey}
            onValueChange={setNewFilterValue}
            onAddFilter={handleAddFilter}
            onRemoveFilter={handleRemoveFilter}
            onClearFilters={handleClearFilters}
          />
        }
      />

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
      <EntityDeleteDialog
        open={deleteDialogOpen}
        entity={entity}
        deleting={deleting}
        onClose={closeDeleteDialog}
        onConfirm={handleDeleteConfirm}
      />
    </Stack>
  );
}

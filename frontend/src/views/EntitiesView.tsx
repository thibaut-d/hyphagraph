import { useEffect, useState, useCallback, useMemo } from "react";
import { listEntities, EntityFilters, getEntityFilterOptions, EntityFilterOptions } from "../api/entities";
import { EntityRead } from "../types/entity";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useNotification } from "../notifications/NotificationContext";

import {
  Typography,
  List,
  ListItem,
  ListItemText,
  Link,
  Paper,
  Box,
  Button,
  Stack,
  Badge,
  Alert,
  CircularProgress,
  Chip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import FilterListIcon from "@mui/icons-material/FilterList";
import UploadIcon from "@mui/icons-material/Upload";
import ClearAllIcon from "@mui/icons-material/ClearAll";

import { FilterDrawer, FilterSection, CheckboxFilter, SearchFilter, RangeFilter } from "../components/filters";
import { ScrollToTop } from "../components/ScrollToTop";
import { ExportMenu } from "../components/ExportMenu";
import { useFilterDrawer } from "../hooks/useFilterDrawer";
import { useFilterOptionsCache } from "../hooks/useFilterOptionsCache";
import { usePersistedFilters } from "../hooks/usePersistedFilters";
import { useDebounce } from "../hooks/useDebounce";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";

const PAGE_SIZE = 50;

export function EntitiesView() {
  const { t, i18n } = useTranslation();
  const { showError } = useNotification();
  const [entities, setEntities] = useState<EntityRead[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);
  const filterOptions = useFilterOptionsCache<EntityFilterOptions>(
    'entity-filter-options-cache',
    getEntityFilterOptions,
  );

  // Filter state with localStorage persistence
  const {
    filters,
    setFilter,
    clearAllFilters,
    activeFilterCount,
  } = usePersistedFilters('entities-filters');

  // Filter drawer UI state
  const {
    isOpen,
    openDrawer,
    closeDrawer,
  } = useFilterDrawer();

  // Debounce search to reduce server load during typing
  const debouncedSearch = useDebounce(filters.search, 300);

  // Extract category options with current language labels
  const categoryOptions = useMemo(() => {
    if (!filterOptions) return [];

    const currentLanguage = i18n.language || 'en';

    return filterOptions.ui_categories.map(cat => ({
      value: cat.id,
      label: cat.label[currentLanguage] || cat.label.en || cat.id
    }));
  }, [filterOptions, i18n.language]);

  // Extract clinical effects options
  const clinicalEffectsOptions = useMemo(() => {
    if (!filterOptions?.clinical_effects) return [];

    const currentLanguage = i18n.language || 'en';

    return filterOptions.clinical_effects.map(effect => ({
      value: effect.type_id,
      label: t(`filters.relation_kind_${effect.type_id}`, effect.label[currentLanguage] || effect.label.en || effect.type_id)
    }));
  }, [filterOptions, i18n.language, t]);

  // Consensus level options (static)
  const consensusOptions = useMemo(() => [
    { value: 'strong', label: t('filters.consensus_strong', 'Strong Consensus (<10% disagreement)') },
    { value: 'moderate', label: t('filters.consensus_moderate', 'Moderate (10-30%)') },
    { value: 'weak', label: t('filters.consensus_weak', 'Weak (30-50%)') },
    { value: 'disputed', label: t('filters.consensus_disputed', 'Disputed (>50%)') },
  ], [t]);

  // Recency options (static)
  const recencyOptions = useMemo(() => [
    { value: 'recent', label: t('filters.recency_recent', 'Recent (<5 years)') },
    { value: 'older', label: t('filters.recency_older', 'Older (5-10 years)') },
    { value: 'historical', label: t('filters.recency_historical', 'Historical (>10 years)') },
  ], [t]);

  // Helper function to get category label from ID
  const getCategoryLabel = useCallback((categoryId: string | undefined) => {
    if (!categoryId) return null;
    const category = categoryOptions.find(opt => opt.value === categoryId);
    return category?.label || null;
  }, [categoryOptions]);

  // Reset pagination when filters change
  useEffect(() => {
    setEntities([]);
    setOffset(0);
    setHasMore(true);
  }, [
    debouncedSearch,
    filters.ui_category_id,
    filters.clinical_effects,
    filters.consensus_level,
    filters.evidence_quality_min,
    filters.evidence_quality_max,
    filters.recency,
    filters.status,
  ]);

  // Fetch entities with server-side filtering and pagination
  const loadEntities = useCallback(async (currentOffset: number) => {
    setIsLoading(true);

    const apiFilters: EntityFilters = {
      limit: PAGE_SIZE,
      offset: currentOffset,
    };

    if (debouncedSearch && typeof debouncedSearch === 'string') {
      apiFilters.search = debouncedSearch;
    }

    if (filters.ui_category_id && Array.isArray(filters.ui_category_id)) {
      apiFilters.ui_category_id = filters.ui_category_id as string[];
    }

    if (filters.clinical_effects && Array.isArray(filters.clinical_effects)) {
      apiFilters.clinical_effects = filters.clinical_effects as string[];
    }

    if (filters.consensus_level && Array.isArray(filters.consensus_level)) {
      apiFilters.consensus_level = filters.consensus_level as string[];
    }

    if (filters.evidence_quality_min !== undefined && filters.evidence_quality_min !== null) {
      apiFilters.evidence_quality_min = filters.evidence_quality_min as number;
    }

    if (filters.evidence_quality_max !== undefined && filters.evidence_quality_max !== null) {
      apiFilters.evidence_quality_max = filters.evidence_quality_max as number;
    }

    if (filters.recency && Array.isArray(filters.recency)) {
      apiFilters.recency = filters.recency as string[];
    }

    if (filters.status && Array.isArray(filters.status)) {
      apiFilters.status = filters.status as string[];
    }

    try {
      const response = await listEntities(apiFilters);

      if (currentOffset === 0) {
        setEntities(response.items);
      } else {
        setEntities(prev => [...prev, ...response.items]);
      }

      setTotal(response.total);
      setHasMore(currentOffset + response.items.length < response.total);
    } catch (err) {
      showError(err);
    } finally {
      setIsLoading(false);
    }
  }, [
    showError,
    debouncedSearch,
    filters.ui_category_id,
    filters.clinical_effects,
    filters.consensus_level,
    filters.evidence_quality_min,
    filters.evidence_quality_max,
    filters.recency,
    filters.status,
  ]);

  useEffect(() => {
    loadEntities(0);
  }, [loadEntities]);

  const handleLoadMore = useCallback(() => {
    const newOffset = offset + PAGE_SIZE;
    setOffset(newOffset);
    loadEntities(newOffset);
  }, [offset, loadEntities]);

  const sentinelRef = useInfiniteScroll({
    onLoadMore: handleLoadMore,
    isLoading,
    hasMore,
  });

  // Build active-filter chip list for inline display (AUD30E-M2)
  const activeFilterChips = useMemo(() => {
    const chips: Array<{ label: string; onDelete: () => void }> = [];
    if (filters.search && typeof filters.search === 'string') {
      chips.push({ label: `"${filters.search}"`, onDelete: () => setFilter('search', '') });
    }
    if (filters.ui_category_id && Array.isArray(filters.ui_category_id)) {
      (filters.ui_category_id as string[]).forEach(id => {
        const label = getCategoryLabel(id) || id;
        chips.push({ label: t('filters.chip_category', 'Category: {{label}}', { label }), onDelete: () => setFilter('ui_category_id', (filters.ui_category_id as string[]).filter(v => v !== id)) });
      });
    }
    if (filters.consensus_level && Array.isArray(filters.consensus_level)) {
      (filters.consensus_level as string[]).forEach(val => {
        const opt = consensusOptions.find(o => o.value === val);
        chips.push({ label: t('filters.chip_consensus', 'Consensus: {{label}}', { label: opt?.label || val }), onDelete: () => setFilter('consensus_level', (filters.consensus_level as string[]).filter(v => v !== val)) });
      });
    }
    if (filters.evidence_quality_min !== undefined && filters.evidence_quality_min !== null) {
      chips.push({ label: t('filters.chip_quality_min', 'Quality ≥ {{val}}%', { val: Math.round((filters.evidence_quality_min as number) * 100) }), onDelete: () => setFilter('evidence_quality_min', null) });
    }
    if (filters.evidence_quality_max !== undefined && filters.evidence_quality_max !== null) {
      chips.push({ label: t('filters.chip_quality_max', 'Quality ≤ {{val}}%', { val: Math.round((filters.evidence_quality_max as number) * 100) }), onDelete: () => setFilter('evidence_quality_max', null) });
    }
    if (filters.recency && Array.isArray(filters.recency)) {
      (filters.recency as string[]).forEach(val => {
        const opt = recencyOptions.find(o => o.value === val);
        chips.push({ label: t('filters.chip_recency', 'Recency: {{label}}', { label: opt?.label || val }), onDelete: () => setFilter('recency', (filters.recency as string[]).filter(v => v !== val)) });
      });
    }
    if (filters.status && Array.isArray(filters.status)) {
      (filters.status as string[]).forEach(val => {
        chips.push({ label: t('filters.chip_status', 'Status: {{val}}', { val }), onDelete: () => setFilter('status', (filters.status as string[]).filter(v => v !== val)) });
      });
    }
    return chips;
  }, [filters, getCategoryLabel, consensusOptions, recencyOptions, setFilter, t]);

  return (
    <Stack spacing={2}>
      <Box sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: { xs: "flex-start", sm: "center" },
        flexDirection: { xs: "column", sm: "row" },
        gap: 2
      }}>
        <Typography variant="h4" sx={{ fontSize: { xs: '1.75rem', sm: '2.125rem' } }}>
          {t("entities.title", "Entities")}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Badge badgeContent={activeFilterCount} color="primary">
            <Button
              variant="outlined"
              startIcon={<FilterListIcon />}
              onClick={openDrawer}
              size="small"
              sx={{ minWidth: { xs: 'auto', sm: 'auto' } }}
            >
              <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                {t("filters.title", "Filters")}
              </Box>
            </Button>
          </Badge>
          <ExportMenu exportType="entities" buttonText={t("entities.export", "Export")} size="small" />
          <Button
            component={RouterLink}
            to="/entities/import"
            variant="outlined"
            startIcon={<UploadIcon />}
            size="small"
          >
            <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
              {t("entities.import", "Import")}
            </Box>
          </Button>
          <Button
            component={RouterLink}
            to="/entities/new"
            variant="contained"
            startIcon={<AddIcon />}
            size="small"
          >
            <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
              {t("entities.create", "Create Entity")}
            </Box>
          </Button>
        </Stack>
      </Box>

      {/* Active filter chips (AUD30E-M2) */}
      {activeFilterChips.length > 0 && (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
          <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
            {t("filters.active_label", "Active filters:")}
          </Typography>
          {activeFilterChips.map((chip) => (
            <Chip
              key={chip.label}
              label={chip.label}
              onDelete={chip.onDelete}
              size="small"
              variant="outlined"
              color="primary"
            />
          ))}
          <Chip
            label={t("filters.clear_all", "Clear all")}
            onClick={clearAllFilters}
            onDelete={clearAllFilters}
            deleteIcon={<ClearAllIcon />}
            size="small"
            variant="filled"
            color="default"
          />
          <Typography variant="caption" color="text.secondary">
            {t("filters.showing_filtered_results", "Showing {{current}} of {{total}} result(s)", { current: entities.length, total })}
          </Typography>
        </Box>
      )}

      <Paper sx={{ p: { xs: 1, sm: 2 } }}>
        {entities.length === 0 && isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: { xs: 2, sm: 3 } }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <List>
              {entities.map((e) => {
                const categoryLabel = getCategoryLabel(e.ui_category_id ?? undefined);
                const consensusColor: Record<string, "success" | "warning" | "error" | "default"> = {
                  strong: "success",
                  moderate: "warning",
                  weak: "error",
                  disputed: "error",
                };
                return (
                  <ListItem key={e.id}>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                          <Link component={RouterLink} to={`/entities/${e.id}`}>
                            {e.slug}
                          </Link>
                          {categoryLabel && (
                            <Chip
                              label={categoryLabel}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                          )}
                          {e.status === "draft" && (
                            <Chip
                              label={t("entity.status_draft", "Draft")}
                              size="small"
                              color="warning"
                              variant="outlined"
                            />
                          )}
                          {e.consensus_level && (
                            <Chip
                              label={t(`filters.consensus_${e.consensus_level}`, e.consensus_level)}
                              size="small"
                              color={consensusColor[e.consensus_level] ?? "default"}
                              variant="outlined"
                            />
                          )}
                        </Box>
                      }
                      secondary={e.summary?.en}
                    />
                  </ListItem>
                );
              })}
            </List>

            {/* Infinite scroll sentinel */}
            <div ref={sentinelRef} style={{ height: '1px' }} />

            {/* Loading indicator for pagination */}
            {isLoading && entities.length > 0 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                <CircularProgress size={24} />
              </Box>
            )}

            {/* Load more button fallback */}
            {hasMore && !isLoading && entities.length > 0 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                <Button variant="outlined" onClick={handleLoadMore}>
                  {t("common.load_more", "Load More")}
                </Button>
              </Box>
            )}
          </>
        )}

        {!isLoading && entities.length === 0 && (
          <Typography color="text.secondary" sx={{ p: 2 }}>
            {activeFilterCount > 0
              ? t("filters.no_results", "No entities match the current filters")
              : t("entities.no_data", "No entities")}
          </Typography>
        )}
      </Paper>

      {/* Filter Drawer */}
      <FilterDrawer
        open={isOpen}
        onClose={closeDrawer}
        title={t("filters.title", "Filters")}
        activeFilterCount={activeFilterCount}
        onClearAll={clearAllFilters}
      >
        {categoryOptions.length > 0 && (
          <FilterSection title={t("filters.entity_category", "Category")}>
            <CheckboxFilter
              options={categoryOptions}
              value={(filters.ui_category_id as string[]) || []}
              onChange={(value) => setFilter('ui_category_id', value)}
            />
          </FilterSection>
        )}

        <FilterSection title={t("filters.search", "Search")}>
          <SearchFilter
            value={(filters.search as string) || ''}
            onChange={(value) => setFilter('search', value)}
            placeholder={t("filters.search_placeholder", "Search by slug...")}
          />
        </FilterSection>

        {/* Advanced Filter: Clinical Effects */}
        {clinicalEffectsOptions.length > 0 && (
          <FilterSection title={t("filters.clinical_effects", "Clinical Effects")}>
            <CheckboxFilter
              options={clinicalEffectsOptions}
              value={(filters.clinical_effects as string[]) || []}
              onChange={(value) => setFilter('clinical_effects', value)}
            />
          </FilterSection>
        )}

        {/* Advanced Filter: Consensus Level */}
        <FilterSection title={t("filters.consensus_level", "Consensus Level")}>
          <CheckboxFilter
            options={consensusOptions}
            value={(filters.consensus_level as string[]) || []}
            onChange={(value) => setFilter('consensus_level', value)}
          />
        </FilterSection>

        {/* Advanced Filter: Evidence Quality */}
        {filterOptions?.evidence_quality_range && (
          <FilterSection title={t("filters.evidence_quality", "Evidence Quality")}>
            <RangeFilter
              value={[
                (filters.evidence_quality_min as number) ?? filterOptions.evidence_quality_range[0],
                (filters.evidence_quality_max as number) ?? filterOptions.evidence_quality_range[1]
              ]}
              onChange={(value) => {
                setFilter('evidence_quality_min', value[0]);
                setFilter('evidence_quality_max', value[1]);
              }}
              min={filterOptions.evidence_quality_range[0]}
              max={filterOptions.evidence_quality_range[1]}
              step={0.05}
              formatValue={(v) => `${(v * 100).toFixed(0)}%`}
            />
          </FilterSection>
        )}

        {/* Advanced Filter: Recency */}
        <FilterSection title={t("filters.recency", "Source Recency")}>
          <CheckboxFilter
            options={recencyOptions}
            value={(filters.recency as string[]) || []}
            onChange={(value) => setFilter('recency', value)}
          />
        </FilterSection>

        {/* Filter: Revision Status */}
        <FilterSection title={t("filters.status", "Status")}>
          <CheckboxFilter
            options={[
              { value: 'draft', label: t('entity.status_draft', 'Draft') },
              { value: 'confirmed', label: t('entity.status_confirmed', 'Confirmed') },
            ]}
            value={(filters.status as string[]) || []}
            onChange={(value) => setFilter('status', value)}
          />
        </FilterSection>
      </FilterDrawer>

      {/* Scroll to top button */}
      <ScrollToTop />
    </Stack>
  );
}

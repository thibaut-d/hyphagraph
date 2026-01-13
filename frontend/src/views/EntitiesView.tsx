import { useEffect, useState, useCallback, useMemo } from "react";
import { listEntities, EntityFilters, getEntityFilterOptions, EntityFilterOptions } from "../api/entities";
import { EntityRead } from "../types/entity";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

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

import { FilterDrawer, FilterSection, CheckboxFilter, SearchFilter, RangeFilter } from "../components/filters";
import { ScrollToTop } from "../components/ScrollToTop";
import { useFilterDrawer } from "../hooks/useFilterDrawer";
import { usePersistedFilters } from "../hooks/usePersistedFilters";
import { useDebounce } from "../hooks/useDebounce";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";

const PAGE_SIZE = 50;
const FILTER_OPTIONS_CACHE_KEY = 'entity-filter-options-cache';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

interface CachedFilterOptions {
  data: EntityFilterOptions;
  timestamp: number;
}

function getCachedFilterOptions(): EntityFilterOptions | null {
  const cached = localStorage.getItem(FILTER_OPTIONS_CACHE_KEY);
  if (!cached) return null;

  try {
    const { data, timestamp }: CachedFilterOptions = JSON.parse(cached);
    if (Date.now() - timestamp > CACHE_TTL) {
      localStorage.removeItem(FILTER_OPTIONS_CACHE_KEY);
      return null;
    }
    return data;
  } catch {
    localStorage.removeItem(FILTER_OPTIONS_CACHE_KEY);
    return null;
  }
}

function setCachedFilterOptions(options: EntityFilterOptions) {
  const cached: CachedFilterOptions = {
    data: options,
    timestamp: Date.now()
  };
  localStorage.setItem(FILTER_OPTIONS_CACHE_KEY, JSON.stringify(cached));
}

export function EntitiesView() {
  const { t, i18n } = useTranslation();
  const [entities, setEntities] = useState<EntityRead[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);
  const [filterOptions, setFilterOptions] = useState<EntityFilterOptions | null>(null);

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

  // Fetch filter options once with caching
  useEffect(() => {
    const cached = getCachedFilterOptions();
    if (cached) {
      setFilterOptions(cached);
    } else {
      getEntityFilterOptions().then(options => {
        setFilterOptions(options);
        setCachedFilterOptions(options);
      });
    }
  }, []);

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
      label: effect.label[currentLanguage] || effect.label.en || effect.type_id
    }));
  }, [filterOptions, i18n.language]);

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
    filters.recency
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
      apiFilters.ui_category_id = filters.ui_category_id;
    }

    if (filters.clinical_effects && Array.isArray(filters.clinical_effects)) {
      apiFilters.clinical_effects = filters.clinical_effects;
    }

    if (filters.consensus_level && Array.isArray(filters.consensus_level)) {
      apiFilters.consensus_level = filters.consensus_level;
    }

    if (filters.evidence_quality_min !== undefined) {
      apiFilters.evidence_quality_min = filters.evidence_quality_min;
    }

    if (filters.evidence_quality_max !== undefined) {
      apiFilters.evidence_quality_max = filters.evidence_quality_max;
    }

    if (filters.recency && Array.isArray(filters.recency)) {
      apiFilters.recency = filters.recency;
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
    } finally {
      setIsLoading(false);
    }
  }, [debouncedSearch, filters.ui_category_id]);

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

      {/* Info when filters are active */}
      {activeFilterCount > 0 && (
        <Alert severity="info" onClose={clearAllFilters}>
          {t(
            "filters.active_count",
            "{{count}} filter(s) active",
            { count: activeFilterCount }
          )}
          {" - "}
          {t(
            "filters.showing_filtered_results",
            "Showing {{current}} of {{total}} result(s)",
            { current: entities.length, total }
          )}
        </Alert>
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
                const categoryLabel = getCategoryLabel(e.ui_category_id);
                return (
                  <ListItem key={e.id}>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
                        </Box>
                      }
                      secondary={e.summary?.en || e.kind}
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
      </FilterDrawer>

      {/* Scroll to top button */}
      <ScrollToTop />
    </Stack>
  );
}

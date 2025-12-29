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
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import FilterListIcon from "@mui/icons-material/FilterList";

import { FilterDrawer, FilterSection, CheckboxFilter, SearchFilter } from "../components/filters";
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

  // Reset pagination when filters change
  useEffect(() => {
    setEntities([]);
    setOffset(0);
    setHasMore(true);
  }, [debouncedSearch, filters.ui_category_id]);

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
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h4">
          {t("entities.title", "Entities")}
        </Typography>
        <Stack direction="row" spacing={2}>
          <Badge badgeContent={activeFilterCount} color="primary">
            <Button
              variant="outlined"
              startIcon={<FilterListIcon />}
              onClick={openDrawer}
            >
              {t("filters.title", "Filters")}
            </Button>
          </Badge>
          <Button
            component={RouterLink}
            to="/entities/new"
            variant="contained"
            startIcon={<AddIcon />}
          >
            {t("entities.create", "Create Entity")}
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

      <Paper sx={{ p: 2 }}>
        {entities.length === 0 && isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <List>
              {entities.map((e) => (
                <ListItem key={e.id}>
                  <ListItemText
                    primary={
                      <Link component={RouterLink} to={`/entities/${e.id}`}>
                        {e.slug}
                      </Link>
                    }
                    secondary={e.summary?.en || e.kind}
                  />
                </ListItem>
              ))}
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
      </FilterDrawer>

      {/* Scroll to top button */}
      <ScrollToTop />
    </Stack>
  );
}

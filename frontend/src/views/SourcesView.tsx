import { useEffect, useState, useMemo, useCallback } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  Link,
  Stack,
  Box,
  Button,
  Badge,
  Alert,
  CircularProgress,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import FilterListIcon from "@mui/icons-material/FilterList";
import DownloadIcon from "@mui/icons-material/Download";

import { listSources, SourceFilters, getSourceFilterOptions, SourceFilterOptions } from "../api/sources";
import { SourceRead } from "../types/source";
import { FilterDrawer, FilterSection, CheckboxFilter, RangeFilter, SearchFilter } from "../components/filters";
import { ScrollToTop } from "../components/ScrollToTop";
import { useFilterDrawer } from "../hooks/useFilterDrawer";
import { usePersistedFilters } from "../hooks/usePersistedFilters";
import { useDebounce } from "../hooks/useDebounce";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";

const PAGE_SIZE = 50;
const FILTER_OPTIONS_CACHE_KEY = 'source-filter-options-cache';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

interface CachedFilterOptions {
  data: SourceFilterOptions;
  timestamp: number;
}

function getCachedFilterOptions(): SourceFilterOptions | null {
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

function setCachedFilterOptions(options: SourceFilterOptions) {
  const cached: CachedFilterOptions = {
    data: options,
    timestamp: Date.now()
  };
  localStorage.setItem(FILTER_OPTIONS_CACHE_KEY, JSON.stringify(cached));
}

export function SourcesView() {
  const { t } = useTranslation();
  const [sources, setSources] = useState<SourceRead[]>([]);
  const [filterOptions, setFilterOptions] = useState<SourceFilterOptions | null>(null);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);

  // Filter state with localStorage persistence
  const {
    filters,
    setFilter,
    clearAllFilters,
    activeFilterCount,
  } = usePersistedFilters('sources-filters');

  // Filter drawer UI state
  const {
    isOpen,
    openDrawer,
    closeDrawer,
  } = useFilterDrawer();

  // Fetch filter options once with caching
  useEffect(() => {
    const cached = getCachedFilterOptions();
    if (cached) {
      setFilterOptions(cached);
    } else {
      getSourceFilterOptions().then(options => {
        setFilterOptions(options);
        setCachedFilterOptions(options);
      });
    }
  }, []);

  // Extract filter options
  const kindOptions = filterOptions?.kinds || [];
  const yearRange = filterOptions?.year_range || null;

  // Debounce search to reduce server load during typing
  const debouncedSearch = useDebounce(filters.search, 300);

  // Reset pagination when filters change
  useEffect(() => {
    setSources([]);
    setOffset(0);
    setHasMore(true);
  }, [filters.kind, filters.year, filters.trust_level, debouncedSearch]);

  // Fetch sources with server-side filtering and pagination
  const loadSources = useCallback(async (currentOffset: number) => {
    setIsLoading(true);

    const apiFilters: SourceFilters = {
      limit: PAGE_SIZE,
      offset: currentOffset,
    };

    if (filters.kind && Array.isArray(filters.kind)) {
      apiFilters.kind = filters.kind;
    }

    if (filters.year && Array.isArray(filters.year) && filters.year.length === 2) {
      const [min, max] = filters.year;
      // Only send year filters if they differ from the full range
      if (!yearRange || min !== yearRange[0] || max !== yearRange[1]) {
        apiFilters.year_min = min;
        apiFilters.year_max = max;
      }
    }

    if (filters.trust_level && Array.isArray(filters.trust_level) && filters.trust_level.length === 2) {
      const [min, max] = filters.trust_level;
      // Only send trust level filters if they differ from defaults
      if (min !== 0 || max !== 1) {
        apiFilters.trust_level_min = min;
        apiFilters.trust_level_max = max;
      }
    }

    if (debouncedSearch && typeof debouncedSearch === 'string') {
      apiFilters.search = debouncedSearch;
    }

    try {
      const response = await listSources(apiFilters);

      if (currentOffset === 0) {
        setSources(response.items);
      } else {
        setSources(prev => [...prev, ...response.items]);
      }

      setTotal(response.total);
      setHasMore(currentOffset + response.items.length < response.total);
    } finally {
      setIsLoading(false);
    }
  }, [filters.kind, filters.year, filters.trust_level, debouncedSearch, yearRange]);

  useEffect(() => {
    loadSources(0);
  }, [loadSources]);

  const handleLoadMore = useCallback(() => {
    const newOffset = offset + PAGE_SIZE;
    setOffset(newOffset);
    loadSources(newOffset);
  }, [offset, loadSources]);

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
          {t("sources.title", "Sources")}
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
            to="/sources/import-pubmed"
            variant="outlined"
            startIcon={<DownloadIcon />}
            size="small"
          >
            <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
              Import from PubMed
            </Box>
          </Button>
          <Button
            component={RouterLink}
            to="/sources/new"
            variant="contained"
            startIcon={<AddIcon />}
            size="small"
          >
            <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
              {t("sources.create", "Create Source")}
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
            { current: sources.length, total }
          )}
        </Alert>
      )}

      <Paper sx={{ p: { xs: 1, sm: 2 } }}>
        {sources.length === 0 && isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: { xs: 2, sm: 3 } }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <List>
              {sources.map((s) => (
                <ListItem key={s.id}>
                  <ListItemText
                    primary={
                      <Link component={RouterLink} to={`/sources/${s.id}`}>
                        {s.title ?? s.id}
                      </Link>
                    }
                    secondary={[
                      s.kind,
                      s.year && `(${s.year})`,
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  />
                </ListItem>
              ))}
            </List>

            {/* Infinite scroll sentinel */}
            <div ref={sentinelRef} style={{ height: '1px' }} />

            {/* Loading indicator for pagination */}
            {isLoading && sources.length > 0 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                <CircularProgress size={24} />
              </Box>
            )}

            {/* Load more button fallback */}
            {hasMore && !isLoading && sources.length > 0 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                <Button variant="outlined" onClick={handleLoadMore}>
                  {t("common.load_more", "Load More")}
                </Button>
              </Box>
            )}
          </>
        )}

        {!isLoading && sources.length === 0 && (
          <Typography color="text.secondary">
            {activeFilterCount > 0
              ? t("filters.no_results", "No sources match the current filters")
              : t("sources.no_data", "No sources")}
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
        <FilterSection title={t("filters.study_type", "Study Type")}>
          <CheckboxFilter
            options={kindOptions}
            value={filters.kind || []}
            onChange={(value) => setFilter('kind', value)}
          />
        </FilterSection>

        {yearRange && (
          <FilterSection title={t("filters.year_range", "Publication Year")}>
            <RangeFilter
              min={yearRange[0]}
              max={yearRange[1]}
              step={1}
              value={filters.year || yearRange}
              onChange={(value) => setFilter('year', value)}
              formatValue={(v) => v.toString()}
            />
          </FilterSection>
        )}

        <FilterSection title={t("filters.trust_level", "Authority Score")}>
          <RangeFilter
            min={0}
            max={1}
            step={0.1}
            value={filters.trust_level || [0, 1]}
            onChange={(value) => setFilter('trust_level', value)}
            formatValue={(v) => v.toFixed(1)}
          />
        </FilterSection>

        <FilterSection title={t("filters.search", "Search")}>
          <SearchFilter
            value={(filters.search as string) || ''}
            onChange={(value) => setFilter('search', value)}
            placeholder={t("filters.search_placeholder_sources", "Search title, authors, origin...")}
          />
        </FilterSection>
      </FilterDrawer>

      {/* Scroll to top button */}
      <ScrollToTop />
    </Stack>
  );
}

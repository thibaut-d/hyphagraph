import { useEffect, useState, useCallback } from "react";
import { listEntities, EntityFilters } from "../api/entities";
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

import { FilterDrawer, FilterSection, SearchFilter } from "../components/filters";
import { useFilterDrawer } from "../hooks/useFilterDrawer";
import { usePersistedFilters } from "../hooks/usePersistedFilters";
import { useDebounce } from "../hooks/useDebounce";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";

const PAGE_SIZE = 50;

export function EntitiesView() {
  const { t } = useTranslation();
  const [entities, setEntities] = useState<EntityRead[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);

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
      const newEntities = await listEntities(apiFilters);

      if (currentOffset === 0) {
        setEntities(newEntities);
      } else {
        setEntities(prev => [...prev, ...newEntities]);
      }

      setHasMore(newEntities.length === PAGE_SIZE);
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
            "Showing {{count}} result(s)",
            { count: entities.length }
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
                        {e.label}
                      </Link>
                    }
                    secondary={e.kind}
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
        <FilterSection title={t("filters.search", "Search")}>
          <SearchFilter
            value={(filters.search as string) || ''}
            onChange={(value) => setFilter('search', value)}
            placeholder={t("filters.search_placeholder", "Search by slug...")}
          />
        </FilterSection>
      </FilterDrawer>
    </Stack>
  );
}

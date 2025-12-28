import { useEffect, useState, useMemo } from "react";
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

import { listSources, SourceFilters } from "../api/sources";
import { SourceRead } from "../types/source";
import { FilterDrawer, FilterSection, CheckboxFilter, RangeFilter, SearchFilter } from "../components/filters";
import { useFilterDrawer } from "../hooks/useFilterDrawer";
import { usePersistedFilters } from "../hooks/usePersistedFilters";
import { deriveFilterOptions, deriveRange } from "../utils/filterUtils";

export function SourcesView() {
  const { t } = useTranslation();
  const [sources, setSources] = useState<SourceRead[]>([]);
  const [allSources, setAllSources] = useState<SourceRead[]>([]);
  const [isLoading, setIsLoading] = useState(false);

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

  // Fetch all sources once for filter options
  useEffect(() => {
    listSources().then(setAllSources);
  }, []);

  // Derive filter options from all sources
  const kindOptions = useMemo(() => deriveFilterOptions(allSources, 'kind'), [allSources]);
  const yearRange = useMemo(() => deriveRange(allSources, 'year'), [allSources]);

  // Fetch sources with server-side filtering
  useEffect(() => {
    setIsLoading(true);

    const apiFilters: SourceFilters = {};

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

    if (filters.search && typeof filters.search === 'string') {
      apiFilters.search = filters.search;
    }

    listSources(apiFilters)
      .then(setSources)
      .finally(() => setIsLoading(false));
  }, [filters, yearRange]);

  return (
    <Stack spacing={2}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h4">
          {t("sources.title", "Sources")}
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
            to="/sources/new"
            variant="contained"
            startIcon={<AddIcon />}
          >
            {t("sources.create", "Create Source")}
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
            { count: sources.length }
          )}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
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
    </Stack>
  );
}
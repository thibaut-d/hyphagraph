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
  Chip,
  CircularProgress,
  Alert,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import FilterListIcon from "@mui/icons-material/FilterList";
import DownloadIcon from "@mui/icons-material/Download";
import SearchIcon from "@mui/icons-material/Search";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import ClearAllIcon from "@mui/icons-material/ClearAll";

import { listSources, SourceFilters, getSourceFilterOptions, SourceFilterOptions } from "../api/sources";
import { SourceRead } from "../types/source";
import { FilterDrawer, FilterSection, CheckboxFilter, RangeFilter, SearchFilter } from "../components/filters";
import { ScrollToTop } from "../components/ScrollToTop";
import { ExportMenu } from "../components/ExportMenu";
import { useFilterDrawer } from "../hooks/useFilterDrawer";
import { useFilterOptionsCache } from "../hooks/useFilterOptionsCache";
import { usePersistedFilters } from "../hooks/usePersistedFilters";
import { useDebounce } from "../hooks/useDebounce";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";

const PAGE_SIZE = 50;

export function SourcesView() {
  const { t } = useTranslation();
  const [sources, setSources] = useState<SourceRead[]>([]);
  const filterOptions = useFilterOptionsCache<SourceFilterOptions>(
    'source-filter-options-cache',
    getSourceFilterOptions,
  );
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
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

  // Extract filter options
  const kindOptions = filterOptions?.kinds || [];
  const yearRange = filterOptions?.year_range || null;
  const domainOptions = filterOptions?.domains || [];
  const roleOptions = filterOptions?.roles || [];

  // Role options with labels
  const roleOptionsWithLabels = useMemo(() => roleOptions.map(role => ({
    value: role,
    label: t(`filters.role_${role}`, role.charAt(0).toUpperCase() + role.slice(1))
  })), [roleOptions, t]);

  // Kind options with labels
  const kindOptionsWithLabels = useMemo(() => kindOptions.map(kind => ({
    value: kind,
    label: t(`sources.kind_${kind}`, kind.charAt(0).toUpperCase() + kind.slice(1))
  })), [kindOptions, t]);

  // Domain options with labels
  const domainOptionsWithLabels = useMemo(() => domainOptions.map(domain => ({
    value: domain,
    label: t(`filters.domain_${domain}`, domain.charAt(0).toUpperCase() + domain.slice(1))
  })), [domainOptions, t]);

  const kindLabelByValue = useMemo(
    () => Object.fromEntries(kindOptionsWithLabels.map((option) => [option.value, option.label])),
    [kindOptionsWithLabels],
  );
  const domainLabelByValue = useMemo(
    () => Object.fromEntries(domainOptionsWithLabels.map((option) => [option.value, option.label])),
    [domainOptionsWithLabels],
  );
  const roleLabelByValue = useMemo(
    () => Object.fromEntries(roleOptionsWithLabels.map((option) => [option.value, option.label])),
    [roleOptionsWithLabels],
  );

  // Debounce search to reduce server load during typing
  const debouncedSearch = useDebounce(filters.search, 300);

  // Build filter params for export — exports only the currently visible (filtered) sources
  const sourceFilterParams = useMemo(() => ({
    ...(filters.kind && Array.isArray(filters.kind) && filters.kind.length > 0 ? { kind: filters.kind as string[] } : {}),
    ...(filters.year && Array.isArray(filters.year) && filters.year.length === 2
      ? { year_min: (filters.year as number[])[0], year_max: (filters.year as number[])[1] }
      : {}),
    ...(filters.trust_level && Array.isArray(filters.trust_level) && filters.trust_level.length === 2
      ? { trust_level_min: (filters.trust_level as number[])[0], trust_level_max: (filters.trust_level as number[])[1] }
      : {}),
    ...(debouncedSearch ? { search: debouncedSearch as string } : {}),
    ...(filters.domain && Array.isArray(filters.domain) && filters.domain.length > 0 ? { domain: filters.domain as string[] } : {}),
    ...(filters.role && Array.isArray(filters.role) && filters.role.length > 0 ? { role: filters.role as string[] } : {}),
  }), [filters.kind, filters.year, filters.trust_level, debouncedSearch, filters.domain, filters.role]);

  // Reset pagination when filters change
  useEffect(() => {
    setIsLoading(true);
    setSources([]);
    setOffset(0);
    setHasMore(true);
  }, [filters.kind, filters.year, filters.trust_level, filters.domain, filters.role, debouncedSearch]);

  // Fetch sources with server-side filtering and pagination
  const loadSources = useCallback(async (currentOffset: number) => {
    setIsLoading(true);

    const apiFilters: SourceFilters = {
      limit: PAGE_SIZE,
      offset: currentOffset,
    };

    if (filters.kind && Array.isArray(filters.kind)) {
      apiFilters.kind = filters.kind as string[];
    }

    if (filters.year && Array.isArray(filters.year) && filters.year.length === 2) {
      const [min, max] = filters.year as [number, number];
      // Only send year filters if they differ from the full range
      if (!yearRange || min !== yearRange[0] || max !== yearRange[1]) {
        apiFilters.year_min = min;
        apiFilters.year_max = max;
      }
    }

    if (filters.trust_level && Array.isArray(filters.trust_level) && filters.trust_level.length === 2) {
      const [min, max] = filters.trust_level as [number, number];
      // Only send trust level filters if they differ from defaults
      if (min !== 0 || max !== 1) {
        apiFilters.trust_level_min = min;
        apiFilters.trust_level_max = max;
      }
    }

    if (debouncedSearch && typeof debouncedSearch === 'string') {
      apiFilters.search = debouncedSearch;
    }

    if (filters.domain && Array.isArray(filters.domain)) {
      apiFilters.domain = filters.domain as string[];
    }

    if (filters.role && Array.isArray(filters.role)) {
      apiFilters.role = filters.role as string[];
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
  }, [
    filters.kind,
    filters.year,
    filters.trust_level,
    filters.domain,
    filters.role,
    debouncedSearch,
    yearRange,
  ]);

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

  const activeFilterChips = useMemo(() => {
    const chips: Array<{ key: string; label: string; onDelete: () => void }> = [];

    if (debouncedSearch && typeof debouncedSearch === "string") {
      chips.push({
        key: `search-${debouncedSearch}`,
        label: t("filters.chip_search", 'Search: "{{value}}"', { value: debouncedSearch }),
        onDelete: () => setFilter("search", ""),
      });
    }

    if (filters.kind && Array.isArray(filters.kind)) {
      (filters.kind as string[]).forEach((value) => {
        chips.push({
          key: `kind-${value}`,
          label: t("filters.chip_kind", "Type: {{label}}", {
            label: kindLabelByValue[value] || value,
          }),
          onDelete: () => setFilter("kind", (filters.kind as string[]).filter((item) => item !== value)),
        });
      });
    }

    if (filters.year && Array.isArray(filters.year) && filters.year.length === 2) {
      const [min, max] = filters.year as number[];
      chips.push({
        key: "year-range",
        label: t("filters.chip_year_range", "Year: {{min}}-{{max}}", { min, max }),
        onDelete: () => setFilter("year", yearRange),
      });
    }

    if (filters.trust_level && Array.isArray(filters.trust_level) && filters.trust_level.length === 2) {
      const [min, max] = filters.trust_level as number[];
      if (min !== 0 || max !== 1) {
        chips.push({
          key: "trust-range",
          label: t("filters.chip_trust_range", "Authority: {{min}}-{{max}}", {
            min: min.toFixed(1),
            max: max.toFixed(1),
          }),
          onDelete: () => setFilter("trust_level", [0, 1]),
        });
      }
    }

    if (filters.domain && Array.isArray(filters.domain)) {
      (filters.domain as string[]).forEach((value) => {
        chips.push({
          key: `domain-${value}`,
          label: t("filters.chip_domain", "Domain: {{label}}", {
            label: domainLabelByValue[value] || value,
          }),
          onDelete: () => setFilter("domain", (filters.domain as string[]).filter((item) => item !== value)),
        });
      });
    }

    if (filters.role && Array.isArray(filters.role)) {
      (filters.role as string[]).forEach((value) => {
        chips.push({
          key: `role-${value}`,
          label: t("filters.chip_role", "Role: {{label}}", {
            label: roleLabelByValue[value] || value,
          }),
          onDelete: () => setFilter("role", (filters.role as string[]).filter((item) => item !== value)),
        });
      });
    }

    return chips;
  }, [
    debouncedSearch,
    filters.kind,
    filters.year,
    filters.trust_level,
    filters.domain,
    filters.role,
    kindLabelByValue,
    domainLabelByValue,
    roleLabelByValue,
    setFilter,
    t,
    yearRange,
  ]);

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
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1.25}
          sx={{ width: { xs: "100%", sm: "auto" } }}
        >
          <Box sx={{ pb: { xs: 0.5, md: 0 } }}>
            <Typography variant="caption" color="text.secondary">
              {t("sources.toolbar_refine", "Refine and export")}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ rowGap: 1 }}>
              <Badge badgeContent={activeFilterCount} color="primary">
                <Button
                  variant="outlined"
                  startIcon={<FilterListIcon />}
                  onClick={openDrawer}
                  size="small"
                >
                  {t("filters.title", "Filters")}
                </Button>
              </Badge>
              <ExportMenu exportType="sources" buttonText={t("export.sources", "Export Sources")} size="small" filterParams={sourceFilterParams} />
              <ExportMenu exportType="relations" buttonText={t("export.relations", "Export Relations")} size="small" filterParams={sourceFilterParams} />
            </Stack>
          </Box>
          <Box sx={{ pb: { xs: 0.5, md: 0 } }}>
            <Typography variant="caption" color="text.secondary">
              {t("sources.toolbar_add", "Discover or add")}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ rowGap: 1 }}>
              <Button
                component={RouterLink}
                to="/sources/smart-discovery"
                variant="contained"
                color="secondary"
                startIcon={<SearchIcon />}
                size="small"
              >
                {t("sources.smart_discovery", "Smart Discovery")}
              </Button>
              <Button
                component={RouterLink}
                to="/sources/import"
                variant="outlined"
                startIcon={<UploadFileIcon />}
                size="small"
              >
                {t("source_import.toolbar_button", "Import")}
              </Button>
              <Button
                component={RouterLink}
                to="/sources/import-pubmed"
                variant="outlined"
                startIcon={<DownloadIcon />}
                size="small"
              >
                {t("sources.import_pubmed", "Import from PubMed")}
              </Button>
              <Button
                component={RouterLink}
                to="/sources/new"
                variant="outlined"
                startIcon={<AddIcon />}
                size="small"
              >
                {t("sources.create", "Create Source")}
              </Button>
            </Stack>
          </Box>
        </Stack>
      </Box>

      {activeFilterChips.length > 0 && (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
          <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
            {t("filters.active_label", "Active filters:")}
          </Typography>
          {activeFilterChips.map((chip) => (
            <Chip
              key={chip.key}
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
          />
          <Alert severity="info" sx={{ py: 0 }}>
            {t("filters.showing_filtered_results", "Showing {{current}} of {{total}} result(s)", {
              current: sources.length,
              total,
            })}
          </Alert>
        </Box>
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
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                        <Link component={RouterLink} to={`/sources/${s.id}`}>
                          {s.title ?? s.id}
                        </Link>
                        {s.trust_level != null && (
                          <Chip
                            label={t("sources.authority_chip", "Authority {{value}}%", {
                              value: Math.round(s.trust_level * 100),
                            })}
                            size="small"
                            color={s.trust_level >= 0.75 ? "success" : "default"}
                            variant="outlined"
                          />
                        )}
                        <Chip
                          label={t("sources.graph_usage_chip", "Used {{count}}x", {
                            count: s.graph_usage_count ?? 0,
                          })}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
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
            options={kindOptionsWithLabels}
            value={(filters.kind as (string | number)[]) || []}
            onChange={(value) => setFilter('kind', value)}
          />
        </FilterSection>

        {yearRange && (
          <FilterSection title={t("filters.year_range", "Publication Year")}>
            <RangeFilter
              min={yearRange[0]}
              max={yearRange[1]}
              step={1}
              value={(filters.year as [number, number]) || yearRange}
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
            value={(filters.trust_level as [number, number]) || [0, 1]}
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

        {/* Advanced Filter: Domain/Topic */}
        {domainOptionsWithLabels.length > 0 && (
          <FilterSection title={t("filters.domain", "Medical Domain")}>
            <CheckboxFilter
              options={domainOptionsWithLabels}
              value={(filters.domain as string[]) || []}
              onChange={(value) => setFilter('domain', value)}
            />
          </FilterSection>
        )}

        {/* Advanced Filter: Role in Graph */}
        {roleOptionsWithLabels.length > 0 && (
          <FilterSection title={t("filters.role_in_graph", "Role in Graph")}>
            <CheckboxFilter
              options={roleOptionsWithLabels}
              value={(filters.role as string[]) || []}
              onChange={(value) => setFilter('role', value)}
            />
          </FilterSection>
        )}
      </FilterDrawer>

      {/* Scroll to top button */}
      <ScrollToTop />
    </Stack>
  );
}

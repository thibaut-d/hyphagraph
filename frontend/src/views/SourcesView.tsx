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
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import FilterListIcon from "@mui/icons-material/FilterList";

import { listSources } from "../api/sources";
import { SourceRead } from "../types/source";
import { FilterDrawer, FilterSection, CheckboxFilter, RangeFilter, YearRangeFilter } from "../components/filters";
import { useFilterDrawer } from "../hooks/useFilterDrawer";
import { useClientSideFilter } from "../hooks/useClientSideFilter";
import { sourcesFilterConfig } from "../config/filterConfigs";
import { deriveFilterOptions, deriveRange } from "../utils/filterUtils";

export function SourcesView() {
  const { t } = useTranslation();
  const [sources, setSources] = useState<SourceRead[]>([]);

  // Filter drawer state
  const {
    isOpen,
    openDrawer,
    closeDrawer,
    filters,
    setFilter,
    clearFilter,
    clearAllFilters,
    activeFilterCount,
  } = useFilterDrawer();

  useEffect(() => {
    listSources().then(setSources);
  }, []);

  // Derive filter options from loaded sources
  const kindOptions = useMemo(() => deriveFilterOptions(sources, 'kind'), [sources]);
  const yearRange = useMemo(() => deriveRange(sources, 'year'), [sources]);

  // Apply filters
  const { filteredItems: filteredSources, hiddenCount } = useClientSideFilter(
    sources,
    filters,
    sourcesFilterConfig
  );

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

      {/* Warning when filters are active */}
      {activeFilterCount > 0 && (
        <Alert severity="info" onClose={clearAllFilters}>
          {t(
            "filters.showing_results",
            "Showing {{count}} of {{total}} results",
            { count: filteredSources.length, total: sources.length }
          )}
          {hiddenCount > 0 && ` (${hiddenCount} hidden by filters)`}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <List>
          {filteredSources.map((s) => (
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

        {filteredSources.length === 0 && sources.length === 0 && (
          <Typography color="text.secondary">
            {t("sources.no_data", "No sources")}
          </Typography>
        )}

        {filteredSources.length === 0 && sources.length > 0 && (
          <Typography color="text.secondary">
            {t("filters.no_results", "No sources match the current filters")}
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
            <YearRangeFilter
              min={yearRange[0]}
              max={yearRange[1]}
              value={filters.year || yearRange}
              onChange={(value) => setFilter('year', value)}
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
      </FilterDrawer>
    </Stack>
  );
}
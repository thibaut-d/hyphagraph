import { useEffect, useState } from "react";
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

export function EntitiesView() {
  const { t } = useTranslation();
  const [entities, setEntities] = useState<EntityRead[]>([]);
  const [isLoading, setIsLoading] = useState(false);

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

  // Fetch entities with server-side filtering
  useEffect(() => {
    setIsLoading(true);

    const apiFilters: EntityFilters = {};

    if (filters.search && typeof filters.search === 'string') {
      apiFilters.search = filters.search;
    }

    if (filters.ui_category_id && Array.isArray(filters.ui_category_id)) {
      apiFilters.ui_category_id = filters.ui_category_id;
    }

    listEntities(apiFilters)
      .then(setEntities)
      .finally(() => setIsLoading(false));
  }, [filters]);

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
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : (
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
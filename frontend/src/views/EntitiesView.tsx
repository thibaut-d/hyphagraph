import { useEffect, useState, useMemo } from "react";
import { listEntities } from "../api/entities";
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
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import FilterListIcon from "@mui/icons-material/FilterList";

import { FilterDrawer, FilterSection, CheckboxFilter } from "../components/filters";
import { useFilterDrawer } from "../hooks/useFilterDrawer";
import { usePersistedFilters } from "../hooks/usePersistedFilters";
import { useClientSideFilter } from "../hooks/useClientSideFilter";
import { entitiesFilterConfig } from "../config/filterConfigs";
import { deriveFilterOptions } from "../utils/filterUtils";

export function EntitiesView() {
  const { t } = useTranslation();
  const [entities, setEntities] = useState<EntityRead[]>([]);

  // Filter state with localStorage persistence
  const {
    filters,
    setFilter,
    clearFilter,
    clearAllFilters,
    activeFilterCount,
  } = usePersistedFilters('entities-filters');

  // Filter drawer UI state
  const {
    isOpen,
    openDrawer,
    closeDrawer,
  } = useFilterDrawer();

  useEffect(() => {
    listEntities().then(setEntities);
  }, []);

  // Derive filter options from loaded entities
  const kindOptions = useMemo(() => deriveFilterOptions(entities, 'kind'), [entities]);

  // Apply filters
  const { filteredItems: filteredEntities, hiddenCount } = useClientSideFilter(
    entities,
    filters,
    entitiesFilterConfig
  );

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

      {/* Warning when filters are active */}
      {activeFilterCount > 0 && (
        <Alert severity="info" onClose={clearAllFilters}>
          {t(
            "filters.showing_results",
            "Showing {{count}} of {{total}} results",
            { count: filteredEntities.length, total: entities.length }
          )}
          {hiddenCount > 0 && ` (${hiddenCount} hidden by filters)`}
        </Alert>
      )}

      <Paper sx={{ p: 2 }}>
        <List>
          {filteredEntities.map((e) => (
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
      </Paper>

      {/* Filter Drawer */}
      <FilterDrawer
        open={isOpen}
        onClose={closeDrawer}
        title={t("filters.title", "Filters")}
        activeFilterCount={activeFilterCount}
        onClearAll={clearAllFilters}
      >
        <FilterSection title={t("filters.entity_type", "Entity Type")}>
          <CheckboxFilter
            options={kindOptions}
            value={filters.kind || []}
            onChange={(value) => setFilter('kind', value)}
          />
        </FilterSection>
      </FilterDrawer>
    </Stack>
  );
}
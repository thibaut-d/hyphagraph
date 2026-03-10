import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack,
  Typography,
  Box,
  Chip,
  TextField,
  Button,
} from "@mui/material";
import FilterListIcon from "@mui/icons-material/FilterList";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { ScopeFilter } from "../../api/inferences";

/**
 * Scope filter panel for entity detail view.
 *
 * Displays active scope filters (key-value pairs) with chips and provides
 * a form to add new filters. Scope filters are server-side filters for
 * narrowing inferences by attributes like population, condition, dosage, etc.
 */
export interface ScopeFilterPanelProps {
  /** Current active scope filters */
  scopeFilter: ScopeFilter;
  /** Form input: new filter key */
  newFilterKey: string;
  /** Form input: new filter value */
  newFilterValue: string;
  /** Callback when key input changes */
  onKeyChange: (value: string) => void;
  /** Callback when value input changes */
  onValueChange: (value: string) => void;
  /** Callback to add a new filter */
  onAddFilter: () => void;
  /** Callback to remove a filter by key */
  onRemoveFilter: (key: string) => void;
  /** Callback to clear all filters */
  onClearFilters: () => void;
}

export function ScopeFilterPanel({
  scopeFilter,
  newFilterKey,
  newFilterValue,
  onKeyChange,
  onValueChange,
  onAddFilter,
  onRemoveFilter,
  onClearFilters,
}: ScopeFilterPanelProps) {
  const activeFilterCount = Object.keys(scopeFilter).length;

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      onAddFilter();
    }
  };

  return (
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack direction="row" spacing={1} alignItems="center">
          <FilterListIcon fontSize="small" />
          <Typography>
            Scope Filter
            {activeFilterCount > 0 && ` (${activeFilterCount} active)`}
          </Typography>
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={2}>
          {/* Active Filters */}
          {activeFilterCount > 0 && (
            <Box>
              <Typography variant="caption" color="text.secondary" gutterBottom>
                Active Filters:
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
                {Object.entries(scopeFilter).map(([key, value]) => (
                  <Chip
                    key={key}
                    label={`${key}: ${value}`}
                    onDelete={() => onRemoveFilter(key)}
                    size="small"
                    color="primary"
                  />
                ))}
              </Stack>
            </Box>
          )}

          {/* Add Filter Form */}
          <Box>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              Add Filter:
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              <TextField
                size="small"
                label="Attribute"
                value={newFilterKey}
                onChange={(e) => onKeyChange(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="e.g., population"
                sx={{ flex: 1 }}
              />
              <TextField
                size="small"
                label="Value"
                value={newFilterValue}
                onChange={(e) => onValueChange(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="e.g., adults"
                sx={{ flex: 1 }}
              />
              <Button
                variant="contained"
                onClick={onAddFilter}
                disabled={!newFilterKey.trim() || !newFilterValue.trim()}
              >
                Add
              </Button>
            </Stack>
          </Box>

          {/* Help Text */}
          <Typography variant="caption" color="text.secondary">
            Filter inferences by scope attributes like population, condition,
            dosage, etc. Only relations matching ALL filter criteria will be
            included in the inference.
          </Typography>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

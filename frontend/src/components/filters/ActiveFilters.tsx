/**
 * ActiveFilters - Display active filters as chips.
 */

import { Stack, Chip, Typography } from '@mui/material';
import type { FilterState, FilterConfig } from '../../types/filters';

export interface ActiveFiltersProps {
  /** Current filter state */
  filters: FilterState;

  /** Filter configurations for labels */
  configs: FilterConfig[];

  /** Called when a filter chip is deleted */
  onDelete: (filterKey: string) => void;
}

/**
 * Display active filters as removable chips.
 */
export function ActiveFilters({ filters, configs, onDelete }: ActiveFiltersProps) {
  // Get human-readable label for filter
  const getFilterLabel = (key: string): string => {
    const config = configs.find((c) => c.id === key);
    return config?.label || key;
  };

  // Format filter value for display
  const formatFilterValue = (key: string, value: any): string => {
    const config = configs.find((c) => c.id === key);

    if (Array.isArray(value)) {
      // For checkbox filters, show count
      return value.length === 1 ? value[0] : `${value.length} selected`;
    }

    if (config?.type === 'range' || config?.type === 'yearRange') {
      const [min, max] = value as [number, number];
      const formatter = config.formatValue || ((v: number) => String(v));
      return `${formatter(min)} - ${formatter(max)}`;
    }

    return String(value);
  };

  const activeFilters = Object.entries(filters).filter(([_, value]) => {
    if (value === undefined || value === null || value === '') return false;
    if (Array.isArray(value) && value.length === 0) return false;
    return true;
  });

  if (activeFilters.length === 0) {
    return null;
  }

  return (
    <Stack spacing={1}>
      <Typography variant="caption" color="text.secondary" sx={{ px: 1 }}>
        Active Filters:
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ px: 1 }}>
        {activeFilters.map(([key, value]) => (
          <Chip
            key={key}
            label={`${getFilterLabel(key)}: ${formatFilterValue(key, value)}`}
            onDelete={() => onDelete(key)}
            size="small"
            sx={{ mb: 1 }}
          />
        ))}
      </Stack>
    </Stack>
  );
}

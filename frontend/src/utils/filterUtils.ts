/**
 * Utility functions for client-side filtering.
 */

import type { FilterConfig, FilterState } from '../types/filters';

/**
 * Apply all active filters to a dataset.
 *
 * Logic:
 * - AND between different filters (all must match)
 * - OR within same filter for arrays (any value can match)
 *
 * @param items - Array of items to filter
 * @param filters - Current filter state
 * @param configs - Filter configurations with filterFn predicates
 * @returns Filtered array of items
 */
export function applyFilters<T>(
  items: T[],
  filters: FilterState,
  configs: FilterConfig<T>[]
): T[] {
  return items.filter((item) => {
    // Item must pass ALL filter configs (AND logic)
    return configs.every((config) => {
      const filterValue = filters[config.id];

      // If filter not set or empty array, pass by default
      if (
        filterValue === undefined ||
        filterValue === null ||
        filterValue === '' ||
        (Array.isArray(filterValue) && filterValue.length === 0)
      ) {
        return true;
      }

      // Apply the filter function
      return config.filterFn(item, filterValue);
    });
  });
}

/**
 * Count the number of active (non-empty) filters.
 *
 * @param filters - Current filter state
 * @returns Count of active filters
 */
export function getActiveFilterCount(filters: FilterState): number {
  return Object.values(filters).filter((value) => {
    if (value === undefined || value === null || value === '') {
      return false;
    }
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return true;
  }).length;
}

/**
 * Extract unique values from a field across all items.
 * Useful for dynamically generating checkbox filter options.
 *
 * @param items - Array of items
 * @param field - Field name to extract
 * @returns Array of unique values (sorted)
 */
export function deriveFilterOptions<T>(
  items: T[],
  field: keyof T
): Array<{ value: string; label: string }> {
  const uniqueValues = new Set<string>();

  items.forEach((item) => {
    const value = item[field];
    if (value !== undefined && value !== null && value !== '') {
      uniqueValues.add(String(value));
    }
  });

  return Array.from(uniqueValues)
    .sort()
    .map((value) => ({
      value,
      label: value,
    }));
}

/**
 * Derive min/max range from numeric field across all items.
 * Useful for auto-configuring range sliders.
 *
 * @param items - Array of items
 * @param field - Numeric field name
 * @returns [min, max] tuple or null if no valid values
 */
export function deriveRange<T>(
  items: T[],
  field: keyof T
): [number, number] | null {
  const values: number[] = [];

  items.forEach((item) => {
    const value = item[field];
    if (typeof value === 'number' && !isNaN(value)) {
      values.push(value);
    }
  });

  if (values.length === 0) {
    return null;
  }

  return [Math.min(...values), Math.max(...values)];
}

/**
 * Hook for applying client-side filters to a dataset.
 *
 * Uses useMemo for performance optimization.
 */

import { useMemo } from 'react';
import type { FilterConfig, FilterState, FilterResult } from '../types/filters';
import { applyFilters } from '../utils/filterUtils';

/**
 * Apply client-side filters to an array of items.
 *
 * @param items - Array of items to filter
 * @param filters - Current filter state
 * @param configs - Filter configurations
 * @returns Filtered items with counts
 */
export function useClientSideFilter<T>(
  items: T[],
  filters: FilterState,
  configs: FilterConfig<T>[]
): FilterResult<T> {
  return useMemo(() => {
    const filteredItems = applyFilters(items, filters, configs);

    return {
      filteredItems,
      totalCount: items.length,
      filteredCount: filteredItems.length,
      hiddenCount: items.length - filteredItems.length,
    };
  }, [items, filters, configs]);
}

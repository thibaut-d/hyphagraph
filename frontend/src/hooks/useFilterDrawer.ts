/**
 * Hook for managing filter drawer state.
 *
 * Provides drawer open/close control and filter state management.
 */

import { useState, useMemo } from 'react';
import type { FilterState } from '../types/filters';
import { getActiveFilterCount } from '../utils/filterUtils';

export interface UseFilterDrawerReturn {
  /** Whether the drawer is open */
  isOpen: boolean;

  /** Open the filter drawer */
  openDrawer: () => void;

  /** Close the filter drawer */
  closeDrawer: () => void;

  /** Current filter state */
  filters: FilterState;

  /** Set a specific filter value */
  setFilter: (key: string, value: any) => void;

  /** Clear a specific filter */
  clearFilter: (key: string) => void;

  /** Clear all filters */
  clearAllFilters: () => void;

  /** Count of active (non-empty) filters */
  activeFilterCount: number;
}

/**
 * Custom hook for managing filter drawer state.
 *
 * @returns Filter drawer state and control functions
 */
export function useFilterDrawer(): UseFilterDrawerReturn {
  const [isOpen, setIsOpen] = useState(false);
  const [filters, setFilters] = useState<FilterState>({});

  const openDrawer = () => setIsOpen(true);
  const closeDrawer = () => setIsOpen(false);

  const setFilter = (key: string, value: any) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const clearFilter = (key: string) => {
    setFilters((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const clearAllFilters = () => {
    setFilters({});
  };

  const activeFilterCount = useMemo(
    () => getActiveFilterCount(filters),
    [filters]
  );

  return {
    isOpen,
    openDrawer,
    closeDrawer,
    filters,
    setFilter,
    clearFilter,
    clearAllFilters,
    activeFilterCount,
  };
}

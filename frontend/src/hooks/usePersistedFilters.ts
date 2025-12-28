/**
 * Hook for managing filters with localStorage persistence.
 *
 * Automatically saves and loads filter state from localStorage,
 * ensuring user preferences persist across sessions.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import type { FilterState } from '../types/filters';
import { getActiveFilterCount } from '../utils/filterUtils';

export interface UsePersistedFiltersReturn {
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
 * Load filters from localStorage.
 *
 * @param storageKey - localStorage key to use
 * @returns Loaded filters or empty object if not found/invalid
 */
function loadFiltersFromStorage(storageKey: string): FilterState {
  try {
    const savedData = localStorage.getItem(storageKey);
    if (!savedData) {
      return {};
    }
    return JSON.parse(savedData);
  } catch (error) {
    console.warn(`Failed to load filters from localStorage (key: ${storageKey}):`, error);
    return {};
  }
}

/**
 * Save filters to localStorage.
 *
 * @param storageKey - localStorage key to use
 * @param filters - Filter state to save
 */
function saveFiltersToStorage(storageKey: string, filters: FilterState): void {
  try {
    localStorage.setItem(storageKey, JSON.stringify(filters));
  } catch (error) {
    console.warn(`Failed to save filters to localStorage (key: ${storageKey}):`, error);
  }
}

/**
 * Check if a filter value is considered "empty" and should not be persisted.
 *
 * @param value - Filter value to check
 * @returns true if value is empty
 */
function isEmptyFilterValue(value: any): boolean {
  if (value === undefined || value === null || value === '') {
    return true;
  }
  if (Array.isArray(value) && value.length === 0) {
    return true;
  }
  return false;
}

/**
 * Custom hook for managing filters with localStorage persistence.
 *
 * @param storageKey - Unique key for localStorage (e.g., "entities-filters")
 * @returns Filter state and control functions
 */
export function usePersistedFilters(storageKey: string): UsePersistedFiltersReturn {
  // Load initial state from localStorage
  const [filters, setFilters] = useState<FilterState>(() =>
    loadFiltersFromStorage(storageKey)
  );

  // Save to localStorage whenever filters change
  useEffect(() => {
    saveFiltersToStorage(storageKey, filters);
  }, [storageKey, filters]);

  const setFilter = useCallback((key: string, value: any) => {
    setFilters((prev) => {
      // Remove filter if value is empty
      if (isEmptyFilterValue(value)) {
        const next = { ...prev };
        delete next[key];
        return next;
      }

      // Otherwise, set the filter
      return {
        ...prev,
        [key]: value,
      };
    });
  }, []);

  const clearFilter = useCallback((key: string) => {
    setFilters((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }, []);

  const clearAllFilters = useCallback(() => {
    setFilters({});
  }, []);

  const activeFilterCount = useMemo(
    () => getActiveFilterCount(filters),
    [filters]
  );

  return {
    filters,
    setFilter,
    clearFilter,
    clearAllFilters,
    activeFilterCount,
  };
}

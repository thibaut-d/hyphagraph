import { useState } from "react";
import { ScopeFilter } from "../api/inferences";

/**
 * Hook for managing scope filter state and operations.
 *
 * Scope filters are key-value pairs used for server-side filtering
 * (e.g., population="elderly", condition="diabetes").
 *
 * Provides state for filter form inputs and operations to add/remove/clear filters.
 * Callbacks receive the updated filter to apply (e.g., trigger a refetch).
 *
 * @returns Scope filter state, form inputs, and filter operations
 */
export interface UseScopeFilterReturn {
  scopeFilter: ScopeFilter;
  newFilterKey: string;
  newFilterValue: string;
  setNewFilterKey: (value: string) => void;
  setNewFilterValue: (value: string) => void;
  addFilter: (key: string, value: string, onApply: (filter: ScopeFilter) => void) => void;
  removeFilter: (key: string, onApply: (filter: ScopeFilter) => void) => void;
  clearFilters: (onApply: (filter: ScopeFilter) => void) => void;
}

export function useScopeFilter(): UseScopeFilterReturn {
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>({});
  const [newFilterKey, setNewFilterKey] = useState("");
  const [newFilterValue, setNewFilterValue] = useState("");

  const addFilter = (key: string, value: string, onApply: (filter: ScopeFilter) => void) => {
    if (!key.trim() || !value.trim()) return;

    const updatedFilter = {
      ...scopeFilter,
      [key.trim()]: value.trim(),
    };
    setScopeFilter(updatedFilter);
    setNewFilterKey("");
    setNewFilterValue("");
    onApply(updatedFilter);
  };

  const removeFilter = (key: string, onApply: (filter: ScopeFilter) => void) => {
    const updatedFilter = { ...scopeFilter };
    delete updatedFilter[key];
    setScopeFilter(updatedFilter);
    onApply(updatedFilter);
  };

  const clearFilters = (onApply: (filter: ScopeFilter) => void) => {
    setScopeFilter({});
    onApply({});
  };

  return {
    scopeFilter,
    newFilterKey,
    newFilterValue,
    setNewFilterKey,
    setNewFilterValue,
    addFilter,
    removeFilter,
    clearFilters,
  };
}

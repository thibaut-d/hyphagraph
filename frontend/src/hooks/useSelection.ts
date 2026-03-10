import { useState, useCallback } from "react";

/**
 * Hook for managing multi-select state.
 *
 * Generic hook for tracking selected IDs with toggle, select all,
 * and clear operations.
 *
 * @param initialSelected - Initial set of selected IDs
 * @returns Selection state and actions
 */
export interface UseSelectionReturn {
  selectedIds: Set<string>;
  toggleSelection: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;
  isSelected: (id: string) => boolean;
  selectedCount: number;
}

export function useSelection(
  initialSelected: Set<string> = new Set()
): UseSelectionReturn {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(initialSelected);

  const toggleSelection = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback((ids: string[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isSelected = useCallback(
    (id: string) => {
      return selectedIds.has(id);
    },
    [selectedIds]
  );

  const selectedCount = selectedIds.size;

  return {
    selectedIds,
    toggleSelection,
    selectAll,
    clearSelection,
    isSelected,
    selectedCount,
  };
}

/**
 * Tests for usePersistedFilters hook.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePersistedFilters } from '../usePersistedFilters';
import type { FilterState } from '../../types/filters';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

describe('usePersistedFilters', () => {
  const storageKey = 'test-filters';

  beforeEach(() => {
    // Clear localStorage before each test
    localStorageMock.clear();
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it('initializes with empty filters when localStorage is empty', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    expect(result.current.filters).toEqual({});
  });

  it('loads filters from localStorage on mount', () => {
    const savedFilters: FilterState = {
      type: ['A', 'B'],
      year: [2020, 2024],
    };
    localStorage.setItem(storageKey, JSON.stringify(savedFilters));

    const { result } = renderHook(() => usePersistedFilters(storageKey));

    expect(result.current.filters).toEqual(savedFilters);
  });

  it('saves filters to localStorage when setFilter is called', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
    });

    const savedData = localStorage.getItem(storageKey);
    expect(savedData).toBe(JSON.stringify({ type: ['A', 'B'] }));
  });

  it('updates multiple filters and persists them', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    act(() => {
      result.current.setFilter('type', ['A']);
      result.current.setFilter('year', [2020, 2024]);
      result.current.setFilter('search', 'test');
    });

    const savedData = localStorage.getItem(storageKey);
    const savedFilters = JSON.parse(savedData!);
    expect(savedFilters).toEqual({
      type: ['A'],
      year: [2020, 2024],
      search: 'test',
    });
  });

  it('removes filter from localStorage when clearFilter is called', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
      result.current.setFilter('year', [2020, 2024]);
    });

    act(() => {
      result.current.clearFilter('type');
    });

    const savedData = localStorage.getItem(storageKey);
    const savedFilters = JSON.parse(savedData!);
    expect(savedFilters).toEqual({ year: [2020, 2024] });
  });

  it('removes all filters from localStorage when clearAllFilters is called', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
      result.current.setFilter('year', [2020, 2024]);
    });

    act(() => {
      result.current.clearAllFilters();
    });

    const savedData = localStorage.getItem(storageKey);
    expect(savedData).toBe('{}');
  });

  it('handles corrupted localStorage data gracefully', () => {
    localStorage.setItem(storageKey, 'invalid json{');

    const { result } = renderHook(() => usePersistedFilters(storageKey));

    // Should fallback to empty filters
    expect(result.current.filters).toEqual({});
  });

  it('handles localStorage quota exceeded error', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    // Mock setItem to throw quota exceeded error
    const originalSetItem = Storage.prototype.setItem;
    Storage.prototype.setItem = vi.fn(() => {
      throw new DOMException('QuotaExceededError');
    });

    // Should not throw error
    expect(() => {
      act(() => {
        result.current.setFilter('type', ['A']);
      });
    }).not.toThrow();

    // Restore original setItem
    Storage.prototype.setItem = originalSetItem;
  });

  it('uses different storage keys for different instances', () => {
    const { result: result1 } = renderHook(() => usePersistedFilters('filters-1'));
    const { result: result2 } = renderHook(() => usePersistedFilters('filters-2'));

    act(() => {
      result1.current.setFilter('type', ['A']);
      result2.current.setFilter('type', ['B']);
    });

    expect(result1.current.filters).toEqual({ type: ['A'] });
    expect(result2.current.filters).toEqual({ type: ['B'] });

    const saved1 = JSON.parse(localStorage.getItem('filters-1')!);
    const saved2 = JSON.parse(localStorage.getItem('filters-2')!);

    expect(saved1).toEqual({ type: ['A'] });
    expect(saved2).toEqual({ type: ['B'] });
  });

  it('persists complex filter values', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    act(() => {
      result.current.setFilter('range', [0.5, 0.9]);
      result.current.setFilter('tags', ['tag1', 'tag2', 'tag3']);
      result.current.setFilter('boolean', true);
    });

    const savedData = localStorage.getItem(storageKey);
    const savedFilters = JSON.parse(savedData!);
    expect(savedFilters).toEqual({
      range: [0.5, 0.9],
      tags: ['tag1', 'tag2', 'tag3'],
      boolean: true,
    });
  });

  it('synchronizes state across multiple renders', () => {
    const { result, rerender } = renderHook(() => usePersistedFilters(storageKey));

    act(() => {
      result.current.setFilter('type', ['A']);
    });

    rerender();

    expect(result.current.filters).toEqual({ type: ['A'] });
  });

  it('does not persist when filter value is empty array', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
    });
    expect(result.current.filters).toEqual({ type: ['A', 'B'] });

    act(() => {
      result.current.setFilter('type', []);
    });

    // Empty array should remove the filter
    const savedData = localStorage.getItem(storageKey);
    const savedFilters = JSON.parse(savedData!);
    expect(savedFilters).toEqual({});
  });

  it('does not persist when filter value is empty string', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    act(() => {
      result.current.setFilter('search', 'test');
    });
    expect(result.current.filters).toEqual({ search: 'test' });

    act(() => {
      result.current.setFilter('search', '');
    });

    // Empty string should remove the filter
    const savedData = localStorage.getItem(storageKey);
    const savedFilters = JSON.parse(savedData!);
    expect(savedFilters).toEqual({});
  });

  it('does not persist when filter value is null', () => {
    const { result } = renderHook(() => usePersistedFilters(storageKey));

    act(() => {
      result.current.setFilter('type', ['A']);
    });
    expect(result.current.filters).toEqual({ type: ['A'] });

    act(() => {
      result.current.setFilter('type', null);
    });

    // Null should remove the filter
    const savedData = localStorage.getItem(storageKey);
    const savedFilters = JSON.parse(savedData!);
    expect(savedFilters).toEqual({});
  });
});

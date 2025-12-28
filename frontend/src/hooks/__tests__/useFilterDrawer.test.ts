/**
 * Tests for useFilterDrawer hook.
 */

import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useFilterDrawer } from '../useFilterDrawer';

describe('useFilterDrawer', () => {
  it('initializes with drawer closed and no filters', () => {
    const { result } = renderHook(() => useFilterDrawer());

    expect(result.current.isOpen).toBe(false);
    expect(result.current.filters).toEqual({});
    expect(result.current.activeFilterCount).toBe(0);
  });

  it('opens drawer when openDrawer is called', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.openDrawer();
    });

    expect(result.current.isOpen).toBe(true);
  });

  it('closes drawer when closeDrawer is called', () => {
    const { result } = renderHook(() => useFilterDrawer());

    // First open
    act(() => {
      result.current.openDrawer();
    });
    expect(result.current.isOpen).toBe(true);

    // Then close
    act(() => {
      result.current.closeDrawer();
    });
    expect(result.current.isOpen).toBe(false);
  });

  it('sets filter value when setFilter is called', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
    });

    expect(result.current.filters).toEqual({ type: ['A', 'B'] });
  });

  it('updates existing filter value', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
    });
    expect(result.current.filters).toEqual({ type: ['A', 'B'] });

    act(() => {
      result.current.setFilter('type', ['C']);
    });
    expect(result.current.filters).toEqual({ type: ['C'] });
  });

  it('sets multiple independent filters', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
      result.current.setFilter('year', [2020, 2024]);
      result.current.setFilter('search', 'test');
    });

    expect(result.current.filters).toEqual({
      type: ['A', 'B'],
      year: [2020, 2024],
      search: 'test',
    });
  });

  it('clears specific filter when clearFilter is called', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
      result.current.setFilter('year', [2020, 2024]);
    });
    expect(result.current.filters).toEqual({
      type: ['A', 'B'],
      year: [2020, 2024],
    });

    act(() => {
      result.current.clearFilter('type');
    });
    expect(result.current.filters).toEqual({ year: [2020, 2024] });
  });

  it('clears all filters when clearAllFilters is called', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
      result.current.setFilter('year', [2020, 2024]);
      result.current.setFilter('search', 'test');
    });
    expect(Object.keys(result.current.filters)).toHaveLength(3);

    act(() => {
      result.current.clearAllFilters();
    });
    expect(result.current.filters).toEqual({});
  });

  it('counts active filters correctly', () => {
    const { result } = renderHook(() => useFilterDrawer());

    expect(result.current.activeFilterCount).toBe(0);

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
    });
    expect(result.current.activeFilterCount).toBe(1);

    act(() => {
      result.current.setFilter('year', [2020, 2024]);
    });
    expect(result.current.activeFilterCount).toBe(2);

    act(() => {
      result.current.setFilter('search', 'test');
    });
    expect(result.current.activeFilterCount).toBe(3);
  });

  it('does not count empty arrays as active filters', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('type', []);
    });

    expect(result.current.activeFilterCount).toBe(0);
  });

  it('does not count empty strings as active filters', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('search', '');
    });

    expect(result.current.activeFilterCount).toBe(0);
  });

  it('does not count null values as active filters', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('type', null);
    });

    expect(result.current.activeFilterCount).toBe(0);
  });

  it('handles clearing non-existent filter gracefully', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.clearFilter('nonExistent');
    });

    expect(result.current.filters).toEqual({});
  });

  it('preserves filter state when drawer is opened and closed', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('type', ['A', 'B']);
      result.current.openDrawer();
    });
    expect(result.current.filters).toEqual({ type: ['A', 'B'] });

    act(() => {
      result.current.closeDrawer();
    });
    expect(result.current.filters).toEqual({ type: ['A', 'B'] });
  });

  it('allows setting filter while drawer is open', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.openDrawer();
      result.current.setFilter('type', ['A', 'B']);
    });

    expect(result.current.isOpen).toBe(true);
    expect(result.current.filters).toEqual({ type: ['A', 'B'] });
  });

  it('handles rapid filter updates', () => {
    const { result } = renderHook(() => useFilterDrawer());

    act(() => {
      result.current.setFilter('search', 't');
      result.current.setFilter('search', 'te');
      result.current.setFilter('search', 'tes');
      result.current.setFilter('search', 'test');
    });

    expect(result.current.filters).toEqual({ search: 'test' });
    expect(result.current.activeFilterCount).toBe(1);
  });
});

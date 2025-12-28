/**
 * Tests for useClientSideFilter hook.
 */

import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useClientSideFilter } from '../useClientSideFilter';
import type { FilterConfig, FilterState } from '../../types/filters';

interface TestItem {
  id: string;
  name: string;
  type: string;
  year?: number;
}

describe('useClientSideFilter', () => {
  const testItems: TestItem[] = [
    { id: '1', name: 'Item 1', type: 'A', year: 2020 },
    { id: '2', name: 'Item 2', type: 'B', year: 2021 },
    { id: '3', name: 'Item 3', type: 'A', year: 2022 },
    { id: '4', name: 'Item 4', type: 'C', year: 2023 },
  ];

  const filterConfigs: FilterConfig<TestItem>[] = [
    {
      id: 'type',
      type: 'checkbox',
      label: 'Type',
      filterFn: (item, selectedTypes: string[]) => {
        if (!selectedTypes || selectedTypes.length === 0) return true;
        return selectedTypes.includes(item.type);
      },
    },
    {
      id: 'year',
      type: 'yearRange',
      label: 'Year',
      filterFn: (item, yearRange: [number, number]) => {
        if (!yearRange || !item.year) return true;
        return item.year >= yearRange[0] && item.year <= yearRange[1];
      },
    },
  ];

  it('returns all items when no filters are active', () => {
    const filters: FilterState = {};

    const { result } = renderHook(() =>
      useClientSideFilter(testItems, filters, filterConfigs)
    );

    expect(result.current.filteredItems).toEqual(testItems);
    expect(result.current.totalCount).toBe(4);
    expect(result.current.filteredCount).toBe(4);
    expect(result.current.hiddenCount).toBe(0);
  });

  it('filters items by checkbox filter', () => {
    const filters: FilterState = { type: ['A', 'B'] };

    const { result } = renderHook(() =>
      useClientSideFilter(testItems, filters, filterConfigs)
    );

    expect(result.current.filteredItems).toHaveLength(3);
    expect(result.current.filteredItems.map((i) => i.id)).toEqual(['1', '2', '3']);
    expect(result.current.totalCount).toBe(4);
    expect(result.current.filteredCount).toBe(3);
    expect(result.current.hiddenCount).toBe(1);
  });

  it('filters items by range filter', () => {
    const filters: FilterState = { year: [2021, 2022] };

    const { result } = renderHook(() =>
      useClientSideFilter(testItems, filters, filterConfigs)
    );

    expect(result.current.filteredItems).toHaveLength(2);
    expect(result.current.filteredItems.map((i) => i.id)).toEqual(['2', '3']);
    expect(result.current.hiddenCount).toBe(2);
  });

  it('applies multiple filters with AND logic', () => {
    const filters: FilterState = {
      type: ['A'],
      year: [2020, 2021],
    };

    const { result } = renderHook(() =>
      useClientSideFilter(testItems, filters, filterConfigs)
    );

    expect(result.current.filteredItems).toHaveLength(1);
    expect(result.current.filteredItems[0].id).toBe('1');
    expect(result.current.hiddenCount).toBe(3);
  });

  it('returns empty result when no items match', () => {
    const filters: FilterState = { type: ['Z'] };

    const { result } = renderHook(() =>
      useClientSideFilter(testItems, filters, filterConfigs)
    );

    expect(result.current.filteredItems).toEqual([]);
    expect(result.current.filteredCount).toBe(0);
    expect(result.current.hiddenCount).toBe(4);
  });

  it('handles empty items array', () => {
    const filters: FilterState = { type: ['A'] };

    const { result } = renderHook(() =>
      useClientSideFilter([], filters, filterConfigs)
    );

    expect(result.current.filteredItems).toEqual([]);
    expect(result.current.totalCount).toBe(0);
    expect(result.current.filteredCount).toBe(0);
    expect(result.current.hiddenCount).toBe(0);
  });

  it('memoizes result when inputs have not changed', () => {
    const filters: FilterState = { type: ['A'] };

    const { result, rerender } = renderHook(() =>
      useClientSideFilter(testItems, filters, filterConfigs)
    );

    const firstResult = result.current;

    // Re-render with same inputs
    rerender();

    // Should return same object reference (memoized)
    expect(result.current).toBe(firstResult);
  });

  it('recalculates when filter state changes', () => {
    const { result, rerender } = renderHook(
      ({ filters }) => useClientSideFilter(testItems, filters, filterConfigs),
      {
        initialProps: { filters: { type: ['A'] } as FilterState },
      }
    );

    expect(result.current.filteredItems).toHaveLength(2);

    // Change filters
    rerender({ filters: { type: ['B'] } });

    expect(result.current.filteredItems).toHaveLength(1);
    expect(result.current.filteredItems[0].type).toBe('B');
  });

  it('recalculates when items change', () => {
    const { result, rerender } = renderHook(
      ({ items }) => useClientSideFilter(items, {}, filterConfigs),
      {
        initialProps: { items: testItems },
      }
    );

    expect(result.current.filteredItems).toHaveLength(4);

    // Change items
    const newItems = testItems.slice(0, 2);
    rerender({ items: newItems });

    expect(result.current.filteredItems).toHaveLength(2);
    expect(result.current.totalCount).toBe(2);
  });

  it('recalculates when filter configs change', () => {
    const filters: FilterState = { type: ['A'] };

    const { result, rerender } = renderHook(
      ({ configs }) => useClientSideFilter(testItems, filters, configs),
      {
        initialProps: { configs: filterConfigs },
      }
    );

    expect(result.current.filteredItems).toHaveLength(2);

    // Change configs (more restrictive)
    const newConfigs: FilterConfig<TestItem>[] = [
      {
        id: 'type',
        type: 'checkbox',
        label: 'Type',
        filterFn: (item, selectedTypes: string[]) => {
          if (!selectedTypes || selectedTypes.length === 0) return true;
          // Also check that year exists
          return selectedTypes.includes(item.type) && item.year !== undefined;
        },
      },
    ];

    rerender({ configs: newConfigs });

    expect(result.current.filteredItems).toHaveLength(2);
  });

  it('handles complex filter combinations', () => {
    const filters: FilterState = {
      type: ['A', 'B', 'C'],
      year: [2021, 2023],
    };

    const { result } = renderHook(() =>
      useClientSideFilter(testItems, filters, filterConfigs)
    );

    // Should match items with type in [A,B,C] AND year in [2021-2023]
    expect(result.current.filteredItems).toHaveLength(3);
    expect(result.current.filteredItems.map((i) => i.id)).toEqual(['2', '3', '4']);
  });

  it('provides correct counts for all scenarios', () => {
    const filters: FilterState = { type: ['A'] };

    const { result } = renderHook(() =>
      useClientSideFilter(testItems, filters, filterConfigs)
    );

    const { totalCount, filteredCount, hiddenCount } = result.current;

    expect(totalCount).toBe(4);
    expect(filteredCount).toBe(2);
    expect(hiddenCount).toBe(2);
    // Verify invariant: totalCount = filteredCount + hiddenCount
    expect(totalCount).toBe(filteredCount + hiddenCount);
  });
});

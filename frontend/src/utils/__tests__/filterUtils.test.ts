/**
 * Tests for filter utility functions.
 */

import { describe, it, expect } from 'vitest';
import {
  applyFilters,
  getActiveFilterCount,
  deriveFilterOptions,
  deriveRange,
} from '../filterUtils';
import type { FilterConfig, FilterState } from '../../types/filters';

interface TestItem {
  id: string;
  name: string;
  type: string;
  year?: number;
  score?: number;
}

describe('filterUtils', () => {
  describe('applyFilters', () => {
    const testItems: TestItem[] = [
      { id: '1', name: 'Item 1', type: 'A', year: 2020, score: 0.8 },
      { id: '2', name: 'Item 2', type: 'B', year: 2021, score: 0.6 },
      { id: '3', name: 'Item 3', type: 'A', year: 2022, score: 0.9 },
      { id: '4', name: 'Item 4', type: 'C', year: 2023, score: 0.7 },
    ];

    it('returns all items when no filters are active', () => {
      const configs: FilterConfig<TestItem>[] = [
        {
          id: 'type',
          type: 'checkbox',
          label: 'Type',
          filterFn: (item, selectedTypes: string[]) =>
            selectedTypes.includes(item.type),
        },
      ];

      const filters: FilterState = {};
      const result = applyFilters(testItems, filters, configs);

      expect(result).toEqual(testItems);
    });

    it('filters items by checkbox filter', () => {
      const configs: FilterConfig<TestItem>[] = [
        {
          id: 'type',
          type: 'checkbox',
          label: 'Type',
          filterFn: (item, selectedTypes: string[]) =>
            selectedTypes.includes(item.type),
        },
      ];

      const filters: FilterState = { type: ['A', 'B'] };
      const result = applyFilters(testItems, filters, configs);

      expect(result).toHaveLength(3);
      expect(result.map((i) => i.id)).toEqual(['1', '2', '3']);
    });

    it('filters items by range filter', () => {
      const configs: FilterConfig<TestItem>[] = [
        {
          id: 'year',
          type: 'yearRange',
          label: 'Year',
          filterFn: (item, yearRange: [number, number]) => {
            if (!item.year) return false;
            return item.year >= yearRange[0] && item.year <= yearRange[1];
          },
        },
      ];

      const filters: FilterState = { year: [2021, 2022] };
      const result = applyFilters(testItems, filters, configs);

      expect(result).toHaveLength(2);
      expect(result.map((i) => i.id)).toEqual(['2', '3']);
    });

    it('applies multiple filters with AND logic', () => {
      const configs: FilterConfig<TestItem>[] = [
        {
          id: 'type',
          type: 'checkbox',
          label: 'Type',
          filterFn: (item, selectedTypes: string[]) =>
            selectedTypes.includes(item.type),
        },
        {
          id: 'year',
          type: 'yearRange',
          label: 'Year',
          filterFn: (item, yearRange: [number, number]) => {
            if (!item.year) return false;
            return item.year >= yearRange[0] && item.year <= yearRange[1];
          },
        },
      ];

      const filters: FilterState = {
        type: ['A', 'B'],
        year: [2021, 2023],
      };
      const result = applyFilters(testItems, filters, configs);

      // Should match items that are (type A OR B) AND (year 2021-2023)
      expect(result).toHaveLength(2);
      expect(result.map((i) => i.id)).toEqual(['2', '3']);
    });

    it('ignores filters with empty array values', () => {
      const configs: FilterConfig<TestItem>[] = [
        {
          id: 'type',
          type: 'checkbox',
          label: 'Type',
          filterFn: (item, selectedTypes: string[]) =>
            selectedTypes.includes(item.type),
        },
      ];

      const filters: FilterState = { type: [] };
      const result = applyFilters(testItems, filters, configs);

      expect(result).toEqual(testItems);
    });

    it('ignores filters with null or undefined values', () => {
      const configs: FilterConfig<TestItem>[] = [
        {
          id: 'type',
          type: 'checkbox',
          label: 'Type',
          filterFn: (item, selectedTypes: string[]) =>
            selectedTypes.includes(item.type),
        },
      ];

      const filters: FilterState = { type: null };
      const result = applyFilters(testItems, filters, configs);

      expect(result).toEqual(testItems);
    });

    it('ignores filters with empty string values', () => {
      const configs: FilterConfig<TestItem>[] = [
        {
          id: 'search',
          type: 'search',
          label: 'Search',
          filterFn: (item, searchTerm: string) =>
            item.name.toLowerCase().includes(searchTerm.toLowerCase()),
        },
      ];

      const filters: FilterState = { search: '' };
      const result = applyFilters(testItems, filters, configs);

      expect(result).toEqual(testItems);
    });

    it('returns empty array when no items match filters', () => {
      const configs: FilterConfig<TestItem>[] = [
        {
          id: 'type',
          type: 'checkbox',
          label: 'Type',
          filterFn: (item, selectedTypes: string[]) =>
            selectedTypes.includes(item.type),
        },
      ];

      const filters: FilterState = { type: ['Z'] };
      const result = applyFilters(testItems, filters, configs);

      expect(result).toEqual([]);
    });

    it('handles items with missing optional fields', () => {
      const itemsWithMissing: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'A', year: 2020 },
        { id: '2', name: 'Item 2', type: 'B' }, // Missing year
      ];

      const configs: FilterConfig<TestItem>[] = [
        {
          id: 'year',
          type: 'yearRange',
          label: 'Year',
          filterFn: (item, yearRange: [number, number]) => {
            if (!item.year) return false;
            return item.year >= yearRange[0] && item.year <= yearRange[1];
          },
        },
      ];

      const filters: FilterState = { year: [2020, 2021] };
      const result = applyFilters(itemsWithMissing, filters, configs);

      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('1');
    });
  });

  describe('getActiveFilterCount', () => {
    it('returns 0 for empty filters', () => {
      const filters: FilterState = {};
      expect(getActiveFilterCount(filters)).toBe(0);
    });

    it('counts non-empty string values', () => {
      const filters: FilterState = { search: 'test' };
      expect(getActiveFilterCount(filters)).toBe(1);
    });

    it('counts non-empty array values', () => {
      const filters: FilterState = { type: ['A', 'B'] };
      expect(getActiveFilterCount(filters)).toBe(1);
    });

    it('counts truthy boolean values', () => {
      const filters: FilterState = { active: true };
      expect(getActiveFilterCount(filters)).toBe(1);
    });

    it('does not count undefined values', () => {
      const filters: FilterState = { search: undefined };
      expect(getActiveFilterCount(filters)).toBe(0);
    });

    it('does not count null values', () => {
      const filters: FilterState = { search: null };
      expect(getActiveFilterCount(filters)).toBe(0);
    });

    it('does not count empty string values', () => {
      const filters: FilterState = { search: '' };
      expect(getActiveFilterCount(filters)).toBe(0);
    });

    it('does not count empty array values', () => {
      const filters: FilterState = { type: [] };
      expect(getActiveFilterCount(filters)).toBe(0);
    });

    it('counts multiple active filters', () => {
      const filters: FilterState = {
        search: 'test',
        type: ['A', 'B'],
        year: [2020, 2024],
        active: true,
      };
      expect(getActiveFilterCount(filters)).toBe(4);
    });

    it('ignores inactive filters in mixed state', () => {
      const filters: FilterState = {
        search: 'test', // active
        type: [], // inactive
        year: [2020, 2024], // active
        category: null, // inactive
        active: true, // active
      };
      expect(getActiveFilterCount(filters)).toBe(3);
    });
  });

  describe('deriveFilterOptions', () => {
    const testItems: TestItem[] = [
      { id: '1', name: 'Item 1', type: 'A' },
      { id: '2', name: 'Item 2', type: 'B' },
      { id: '3', name: 'Item 3', type: 'A' },
      { id: '4', name: 'Item 4', type: 'C' },
    ];

    it('extracts unique values from field', () => {
      const options = deriveFilterOptions(testItems, 'type');

      expect(options).toEqual([
        { value: 'A', label: 'A' },
        { value: 'B', label: 'B' },
        { value: 'C', label: 'C' },
      ]);
    });

    it('sorts options alphabetically', () => {
      const items: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'Z' },
        { id: '2', name: 'Item 2', type: 'A' },
        { id: '3', name: 'Item 3', type: 'M' },
      ];

      const options = deriveFilterOptions(items, 'type');

      expect(options.map((o) => o.value)).toEqual(['A', 'M', 'Z']);
    });

    it('excludes undefined values', () => {
      const items: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'A', year: undefined },
        { id: '2', name: 'Item 2', type: 'B', year: 2020 },
      ];

      const options = deriveFilterOptions(items, 'year');

      expect(options).toEqual([{ value: '2020', label: '2020' }]);
    });

    it('excludes null values', () => {
      const items: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'A', year: 2020 },
        { id: '2', name: 'Item 2', type: 'B', year: null as any },
      ];

      const options = deriveFilterOptions(items, 'year');

      expect(options).toEqual([{ value: '2020', label: '2020' }]);
    });

    it('excludes empty string values', () => {
      const items: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'A' },
        { id: '2', name: 'Item 2', type: '' },
      ];

      const options = deriveFilterOptions(items, 'type');

      expect(options).toEqual([{ value: 'A', label: 'A' }]);
    });

    it('returns empty array for empty items', () => {
      const options = deriveFilterOptions([], 'type');
      expect(options).toEqual([]);
    });

    it('handles numeric field values', () => {
      const items: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'A', year: 2020 },
        { id: '2', name: 'Item 2', type: 'B', year: 2021 },
        { id: '3', name: 'Item 3', type: 'C', year: 2020 },
      ];

      const options = deriveFilterOptions(items, 'year');

      expect(options).toEqual([
        { value: '2020', label: '2020' },
        { value: '2021', label: '2021' },
      ]);
    });
  });

  describe('deriveRange', () => {
    const testItems: TestItem[] = [
      { id: '1', name: 'Item 1', type: 'A', year: 2020, score: 0.5 },
      { id: '2', name: 'Item 2', type: 'B', year: 2022, score: 0.8 },
      { id: '3', name: 'Item 3', type: 'C', year: 2021, score: 0.3 },
    ];

    it('returns min and max for numeric field', () => {
      const range = deriveRange(testItems, 'year');

      expect(range).toEqual([2020, 2022]);
    });

    it('returns min and max for decimal field', () => {
      const range = deriveRange(testItems, 'score');

      expect(range).toEqual([0.3, 0.8]);
    });

    it('handles items with single value', () => {
      const items: TestItem[] = [{ id: '1', name: 'Item 1', type: 'A', year: 2020 }];

      const range = deriveRange(items, 'year');

      expect(range).toEqual([2020, 2020]);
    });

    it('ignores undefined values', () => {
      const items: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'A', year: 2020 },
        { id: '2', name: 'Item 2', type: 'B', year: undefined },
        { id: '3', name: 'Item 3', type: 'C', year: 2022 },
      ];

      const range = deriveRange(items, 'year');

      expect(range).toEqual([2020, 2022]);
    });

    it('ignores NaN values', () => {
      const items: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'A', score: 0.5 },
        { id: '2', name: 'Item 2', type: 'B', score: NaN },
        { id: '3', name: 'Item 3', type: 'C', score: 0.8 },
      ];

      const range = deriveRange(items, 'score');

      expect(range).toEqual([0.5, 0.8]);
    });

    it('returns null for empty items', () => {
      const range = deriveRange([], 'year');

      expect(range).toBeNull();
    });

    it('returns null when all values are undefined', () => {
      const items: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'A', year: undefined },
        { id: '2', name: 'Item 2', type: 'B', year: undefined },
      ];

      const range = deriveRange(items, 'year');

      expect(range).toBeNull();
    });

    it('returns null for non-numeric field', () => {
      const range = deriveRange(testItems, 'type' as any);

      expect(range).toBeNull();
    });

    it('handles negative numbers', () => {
      const items: TestItem[] = [
        { id: '1', name: 'Item 1', type: 'A', score: -0.5 },
        { id: '2', name: 'Item 2', type: 'B', score: 0.5 },
        { id: '3', name: 'Item 3', type: 'C', score: -1.0 },
      ];

      const range = deriveRange(items, 'score');

      expect(range).toEqual([-1.0, 0.5]);
    });
  });
});

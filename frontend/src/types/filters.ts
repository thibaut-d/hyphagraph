/**
 * Filter system type definitions.
 *
 * Supports client-side filtering with multiple filter types:
 * - checkbox: Multi-select from list of options
 * - range: Min/max numeric range
 * - yearRange: Year-specific range (no decimals)
 * - search: Text search with debounce
 */

/**
 * Option for checkbox filters
 */
export interface FilterOption {
  value: string | number;
  label: string;
}

/**
 * Filter configuration defining behavior and display
 */
export interface FilterConfig<T = any> {
  /** Unique identifier for this filter */
  id: string;

  /** Type of filter UI component */
  type: 'checkbox' | 'range' | 'yearRange' | 'search';

  /** i18n key for filter label */
  label: string;

  /** Predicate function to test if item matches filter value */
  filterFn: (item: T, filterValue: any) => boolean;

  /** Options for checkbox filters */
  options?: FilterOption[];

  /** Minimum value for range filters */
  min?: number;

  /** Maximum value for range filters */
  max?: number;

  /** Step size for range sliders */
  step?: number;

  /** Optional value formatter for display */
  formatValue?: (value: number) => string;
}

/**
 * Current state of all active filters
 * Key = filter ID, Value = filter value (type depends on filter type)
 */
export interface FilterState {
  [filterKey: string]: any;
}

/**
 * Result of applying filters to a dataset
 */
export interface FilterResult<T> {
  /** Items that passed all filters */
  filteredItems: T[];

  /** Total number of items before filtering */
  totalCount: number;

  /** Number of items after filtering */
  filteredCount: number;

  /** Number of items hidden by filters */
  hiddenCount: number;
}

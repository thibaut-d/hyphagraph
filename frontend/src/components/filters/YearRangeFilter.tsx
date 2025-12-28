/**
 * YearRangeFilter - Year-specific range filter (no decimals).
 */

import { RangeFilter, RangeFilterProps } from './RangeFilter';

export type YearRangeFilterProps = Omit<RangeFilterProps, 'step' | 'formatValue'>;

/**
 * Year range filter (extends RangeFilter with integer years).
 */
export function YearRangeFilter(props: YearRangeFilterProps) {
  return (
    <RangeFilter
      {...props}
      step={1}
      formatValue={(v) => String(Math.round(v))}
    />
  );
}

/**
 * Filter configurations for entities and sources.
 *
 * Defines available filters for each view with their behavior and display properties.
 */

import type { FilterConfig } from '../types/filters';
import type { EntityRead } from '../types/entity';
import type { SourceRead } from '../types/source';

/**
 * Filter configuration for Entities List view.
 */
export const entitiesFilterConfig: FilterConfig<EntityRead>[] = [
  {
    id: 'kind',
    type: 'checkbox',
    label: 'filters.entity_type',
    filterFn: (entity, selectedKinds: string[]) => {
      if (!selectedKinds || selectedKinds.length === 0) return true;
      return selectedKinds.includes(entity.kind || '');
    },
    options: [], // Populated dynamically from data
  },
  {
    id: 'ui_category',
    type: 'checkbox',
    label: 'filters.category',
    filterFn: (entity, selectedCategories: string[]) => {
      if (!selectedCategories || selectedCategories.length === 0) return true;
      if (!entity.ui_category_id) return false;
      return selectedCategories.includes(entity.ui_category_id);
    },
    options: [], // Populated dynamically from data
  },
];

/**
 * Filter configuration for Sources List view.
 */
export const sourcesFilterConfig: FilterConfig<SourceRead>[] = [
  {
    id: 'kind',
    type: 'checkbox',
    label: 'filters.study_type',
    filterFn: (source, selectedKinds: string[]) => {
      if (!selectedKinds || selectedKinds.length === 0) return true;
      return selectedKinds.includes(source.kind);
    },
    options: [], // Populated dynamically from data
  },
  {
    id: 'year',
    type: 'yearRange',
    label: 'filters.year_range',
    filterFn: (source, yearRange: [number, number] | null) => {
      if (!yearRange || !source.year) return true;
      const [min, max] = yearRange;
      return source.year >= min && source.year <= max;
    },
    min: 1900, // Will be overridden dynamically
    max: new Date().getFullYear(),
  },
  {
    id: 'trust_level',
    type: 'range',
    label: 'filters.trust_level',
    filterFn: (source, trustRange: [number, number] | null) => {
      if (!trustRange) return true;
      const trustLevel = source.trust_level ?? 0.5;
      const [min, max] = trustRange;
      return trustLevel >= min && trustLevel <= max;
    },
    min: 0,
    max: 1,
    step: 0.1,
    formatValue: (v) => v.toFixed(1),
  },
];

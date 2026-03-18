import { useMemo } from "react";
import { InferenceRead } from "../types/inference";
import { SourceRead } from "../types/source";
import { EntityDetailFilterValues } from "../components/filters";

/**
 * Hook for applying client-side evidence filters to inference data.
 *
 * Filters relations by:
 * - Direction (incoming/outgoing)
 * - Relation kind
 * - Source year range
 * - Source trust level
 *
 * Returns filtered inference and relation counts for UI feedback.
 *
 * @param inference - The raw inference data
 * @param filters - The active evidence filters
 * @param sources - Source data cache for year/trust filtering
 * @param activeFilterCount - Number of active filters (optimization)
 * @returns Filtered inference and relation counts
 */
export interface UseInferenceFilteringReturn {
  filteredInference: InferenceRead | null;
  totalRelationsCount: number;
  filteredRelationsCount: number;
  hiddenRelationsCount: number;
}

export function useInferenceFiltering(
  inference: InferenceRead | null,
  filters: EntityDetailFilterValues,
  sources: Record<string, SourceRead>,
  activeFilterCount: number
): UseInferenceFilteringReturn {
  const filteredInference = useMemo(() => {
    if (!inference || activeFilterCount === 0) {
      return inference;
    }

    const filtered: InferenceRead = {
      entity_id: inference.entity_id,
      relations_by_kind: {},
    };

    Object.entries(inference.relations_by_kind).forEach(([kind, relations]) => {
      const filteredRelations = relations.filter((rel) => {
        // Direction filter
        if (filters.directions && filters.directions.length > 0) {
          if (!filters.directions.includes(rel.direction ?? "")) {
            return false;
          }
        }

        // Kind filter
        if (filters.kinds && filters.kinds.length > 0 && rel.kind && !filters.kinds.includes(rel.kind)) {
          return false;
        }

        // Year range filter (requires source data)
        const source = sources[rel.source_id];
        if (source) {
          const [yearStart, yearEnd] = filters.yearRange ?? [undefined, undefined];
          if (yearStart !== undefined && source.year && source.year < yearStart) {
            return false;
          }
          if (yearEnd !== undefined && source.year && source.year > yearEnd) {
            return false;
          }

          // Trust level filter
          if (filters.minTrustLevel !== undefined && source.trust_level !== null) {
            if ((source.trust_level ?? 0) < filters.minTrustLevel) {
              return false;
            }
          }
        }

        return true;
      });

      if (filteredRelations.length > 0) {
        filtered.relations_by_kind[kind] = filteredRelations;
      }
    });

    return filtered;
  }, [inference, filters, sources, activeFilterCount]);

  const totalRelationsCount = useMemo(() => {
    if (!inference) return 0;
    return Object.values(inference.relations_by_kind).reduce(
      (sum, relations) => sum + relations.length,
      0
    );
  }, [inference]);

  const filteredRelationsCount = useMemo(() => {
    if (!filteredInference) return 0;
    return Object.values(filteredInference.relations_by_kind).reduce(
      (sum, relations) => sum + relations.length,
      0
    );
  }, [filteredInference]);

  const hiddenRelationsCount = totalRelationsCount - filteredRelationsCount;

  return {
    filteredInference,
    totalRelationsCount,
    filteredRelationsCount,
    hiddenRelationsCount,
  };
}

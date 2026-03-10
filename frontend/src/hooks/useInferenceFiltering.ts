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
      entity: inference.entity,
      relations_by_kind: {},
    };

    Object.entries(inference.relations_by_kind).forEach(([kind, relations]) => {
      const filteredRelations = relations.filter((rel) => {
        // Direction filter
        if (filters.direction && filters.direction !== "all") {
          if (filters.direction === "incoming" && rel.direction !== "incoming") {
            return false;
          }
          if (filters.direction === "outgoing" && rel.direction !== "outgoing") {
            return false;
          }
        }

        // Kind filter
        if (filters.kind && rel.kind !== filters.kind) {
          return false;
        }

        // Year range filter (requires source data)
        const source = sources[rel.source_id];
        if (source) {
          if (filters.yearStart !== undefined && source.year && source.year < filters.yearStart) {
            return false;
          }
          if (filters.yearEnd !== undefined && source.year && source.year > filters.yearEnd) {
            return false;
          }

          // Trust level filter
          if (filters.minTrust !== undefined && source.trust_level !== null) {
            if (source.trust_level < filters.minTrust) {
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

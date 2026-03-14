import { useState, useEffect, useRef } from "react";
import { InferenceRead } from "../types/inference";
import { SourceRead } from "../types/source";
import { ScopeFilter, getInferenceForEntity } from "../api/inferences";
import { getSource } from "../api/sources";
import { ParsedAppError } from "../utils/errorHandler";
import { usePageErrorHandler } from "./usePageErrorHandler";

/**
 * Hook for fetching and managing entity inference data with source cache.
 *
 * Fetches inference data for an entity with optional scope filtering.
 * Automatically fetches and caches source data for all relations in the inference.
 * Handles source fetch errors gracefully (logs but doesn't fail).
 *
 * @param entityId - The ID of the entity
 * @param initialScopeFilter - Optional initial scope filter to apply
 * @returns Inference data, sources cache, loading state, and loadInference function
 */
export interface UseEntityInferenceReturn {
  inference: InferenceRead | null;
  sources: Record<string, SourceRead>;
  loadingSources: boolean;
  error: Error | null;
  loadInference: (filter: ScopeFilter) => Promise<void>;
}

export function useEntityInference(
  entityId: string | undefined,
  initialScopeFilter: ScopeFilter = {}
): UseEntityInferenceReturn {
  const handlePageError = usePageErrorHandler();
  const [inference, setInference] = useState<InferenceRead | null>(null);
  const [sources, setSources] = useState<Record<string, SourceRead>>({});
  const [loadingSources, setLoadingSources] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const requestIdRef = useRef(0);

  const loadInference = async (filter: ScopeFilter) => {
    const requestId = ++requestIdRef.current;

    if (!entityId) {
      setInference(null);
      setSources({});
      setError(new Error("Missing entity ID"));
      setLoadingSources(false);
      return;
    }

    try {
      setError(null);
      const inferenceRes = await getInferenceForEntity(entityId, filter);
      if (requestId !== requestIdRef.current) {
        return;
      }

      setInference(inferenceRes);

      // Extract unique source IDs from relations
      const sourceIds = new Set<string>();
      Object.values(inferenceRes.relations_by_kind).forEach((relations) => {
        relations.forEach((rel) => {
          sourceIds.add(rel.source_id);
        });
      });

      // Fetch all source data for filtering
      if (sourceIds.size > 0) {
        setLoadingSources(true);
        const sourcePromises = Array.from(sourceIds).map(async (sourceId) => {
          try {
            return await getSource(sourceId);
          } catch (err) {
            console.error(`Failed to fetch source ${sourceId}:`, err);
            return null;
          }
        });

        const sourcesArray = await Promise.all(sourcePromises);
        const sourcesMap: Record<string, SourceRead> = {};
        sourcesArray.forEach((source) => {
          if (source) {
            sourcesMap[source.id] = source;
          }
        });
        if (requestId !== requestIdRef.current) {
          return;
        }

        setSources(sourcesMap);
        setLoadingSources(false);
        return;
      }

      setSources({});
      setLoadingSources(false);
    } catch (err) {
      if (requestId !== requestIdRef.current) {
        return;
      }

      const parsedError = handlePageError(err, "Failed to load inference");
      const nextError =
        err instanceof Error ? err : new ParsedAppError(parsedError);

      setInference(null);
      setSources({});
      setLoadingSources(false);
      setError(nextError);
    }
  };

  useEffect(() => {
    loadInference(initialScopeFilter);
  }, [entityId]);

  return {
    inference,
    sources,
    loadingSources,
    error,
    loadInference,
  };
}

import { useState, useEffect, useRef } from "react";
import { EntityRead } from "../types/entity";
import { getEntity } from "../api/entities";
import { useNotification } from "../notifications/NotificationContext";
import { parseError, ParsedAppError } from "../utils/errorHandler";

/**
 * Hook for fetching and managing entity data.
 *
 * Handles entity data fetching with loading and error states.
 * Automatically refetches when entityId changes.
 *
 * @param entityId - The ID of the entity to fetch
 * @returns Entity data, loading state, error state, and refetch function
 */
export interface UseEntityDataReturn {
  entity: EntityRead | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useEntityData(entityId: string | undefined): UseEntityDataReturn {
  const { showError } = useNotification();
  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const requestIdRef = useRef(0);

  const fetchEntity = async () => {
    const requestId = ++requestIdRef.current;

    if (!entityId) {
      setEntity(null);
      setError(new Error("Missing entity ID"));
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const entityRes = await getEntity(entityId);
      if (requestId !== requestIdRef.current) {
        return;
      }
      setEntity(entityRes);
    } catch (err) {
      if (requestId !== requestIdRef.current) {
        return;
      }

      const parsedError = parseError(err, "Failed to load entity");
      const nextError =
        err instanceof Error ? err : new ParsedAppError(parsedError);

      setEntity(null);
      setError(nextError);
      showError(err);
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchEntity();
  }, [entityId]);

  return {
    entity,
    loading,
    error,
    refetch: fetchEntity,
  };
}

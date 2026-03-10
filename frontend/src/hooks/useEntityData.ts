import { useState, useEffect } from "react";
import { EntityRead } from "../types/entity";
import { getEntity } from "../api/entities";
import { useNotification } from "../notifications/NotificationContext";

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

  const fetchEntity = async () => {
    if (!entityId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const entityRes = await getEntity(entityId);
      setEntity(entityRes);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      showError(error);
    } finally {
      setLoading(false);
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

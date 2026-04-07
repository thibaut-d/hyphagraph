import { useCallback } from "react";

import { getEntity } from "../api/entities";
import { getInferenceDetailForEntity } from "../api/inferences";
import type { EntityRead } from "../types/entity";
import type { InferenceDetailRead } from "../types/inference";
import { useAsyncResource } from "./useAsyncResource";
import { usePageErrorHandler } from "./usePageErrorHandler";

export interface EntityInferenceDetail {
  entity: EntityRead;
  inference: InferenceDetailRead | null;
}

export function useEntityInferenceDetail(
  entityId: string | undefined,
  fallbackMessage: string
) {
  const handlePageError = usePageErrorHandler();

  const load = useCallback(async (): Promise<EntityInferenceDetail> => {
    if (!entityId) {
      throw new Error("Missing entity ID");
    }

    const entity = await getEntity(entityId);
    const inference = await getInferenceDetailForEntity(entity.id);

    return { entity, inference };
  }, [entityId]);

  return useAsyncResource<EntityInferenceDetail>({
    enabled: true,
    deps: [entityId],
    load,
    onError: (error) => handlePageError(error, fallbackMessage).userMessage,
  });
}

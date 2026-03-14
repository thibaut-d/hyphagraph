import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { listEntities } from "../api/entities";
import type { EntityRead } from "../types/entity";
import { usePageErrorHandler } from "./usePageErrorHandler";

const ENTITY_PAGE_SIZE = 100;
const ENTITY_MAX_PAGES = 50;

interface DiscoveryEntitiesState {
  availableEntities: EntityRead[];
  selectedEntities: EntityRead[];
  setSelectedEntities: React.Dispatch<React.SetStateAction<EntityRead[]>>;
  loadingEntities: boolean;
  entityLoadError: string | null;
}

export function useDiscoveryEntities(): DiscoveryEntitiesState {
  const [searchParams] = useSearchParams();
  const handlePageError = usePageErrorHandler();

  const [availableEntities, setAvailableEntities] = useState<EntityRead[]>([]);
  const [selectedEntities, setSelectedEntities] = useState<EntityRead[]>([]);
  const [loadingEntities, setLoadingEntities] = useState(false);
  const [entityLoadError, setEntityLoadError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadEntities = async () => {
      setLoadingEntities(true);
      setEntityLoadError(null);

      try {
        const allEntities: EntityRead[] = [];
        let offset = 0;
        let total = 0;
        let pages = 0;
        let hasMore = true;

        while (hasMore && pages < ENTITY_MAX_PAGES) {
          const response = await listEntities({ limit: ENTITY_PAGE_SIZE, offset });
          allEntities.push(...response.items);
          total = response.total;
          offset += response.items.length;
          pages += 1;
          hasMore = response.items.length > 0 && allEntities.length < total;
        }

        const dedupedEntities = Array.from(
          new Map(allEntities.map((entity) => [entity.id, entity])).values()
        );

        const entitySlugParam = searchParams.get("entity");
        let preselectedEntity: EntityRead | undefined;
        if (entitySlugParam) {
          preselectedEntity = dedupedEntities.find((entity) => entity.slug === entitySlugParam);

          if (!preselectedEntity) {
            const searchResponse = await listEntities({
              search: entitySlugParam,
              limit: ENTITY_PAGE_SIZE,
              offset: 0,
            });
            preselectedEntity = searchResponse.items.find((entity) => entity.slug === entitySlugParam);
            if (preselectedEntity && !dedupedEntities.some((entity) => entity.id === preselectedEntity.id)) {
              dedupedEntities.push(preselectedEntity);
            }
          }
        }

        if (!isMounted) {
          return;
        }

        setAvailableEntities(dedupedEntities);
        if (preselectedEntity) {
          setSelectedEntities([preselectedEntity]);
        }
      } catch (error) {
        if (isMounted) {
          setEntityLoadError(handlePageError(error, "Failed to load entities").userMessage);
        }
      } finally {
        if (isMounted) {
          setLoadingEntities(false);
        }
      }
    };

    void loadEntities();

    return () => {
      isMounted = false;
    };
  }, [handlePageError, searchParams]);

  return {
    availableEntities,
    selectedEntities,
    setSelectedEntities,
    loadingEntities,
    entityLoadError,
  };
}

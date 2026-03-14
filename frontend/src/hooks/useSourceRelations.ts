import { type Dispatch, type SetStateAction, useCallback, useState } from "react";

import { listRelationsBySource } from "../api/relations";
import type { RelationRead } from "../types/relation";
import { usePageErrorHandler } from "./usePageErrorHandler";

interface SourceRelationsState {
  relations: RelationRead[];
  relationsError: string | null;
  reloadRelations: () => Promise<RelationRead[]>;
  setRelations: Dispatch<SetStateAction<RelationRead[]>>;
}

export function useSourceRelations(sourceId?: string): SourceRelationsState {
  const handlePageError = usePageErrorHandler();
  const [relations, setRelations] = useState<RelationRead[]>([]);
  const [relationsError, setRelationsError] = useState<string | null>(null);

  const reloadRelations = useCallback(async (): Promise<RelationRead[]> => {
    if (!sourceId) {
      setRelations([]);
      setRelationsError("Missing source ID");
      return [];
    }

    try {
      const nextRelations = await listRelationsBySource(sourceId);
      setRelations(nextRelations);
      setRelationsError(null);
      return nextRelations;
    } catch (error) {
      const parsedError = handlePageError(error, "Failed to load relations");
      setRelations([]);
      setRelationsError(parsedError.userMessage);
      return [];
    }
  }, [handlePageError, sourceId]);

  return {
    relations,
    relationsError,
    reloadRelations,
    setRelations,
  };
}

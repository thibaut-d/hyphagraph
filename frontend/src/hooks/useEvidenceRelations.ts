import { useEffect, useState } from "react";

import { getSource } from "../api/sources";
import type { InferenceRead } from "../types/inference";
import type { RelationRead } from "../types/relation";
import type { SourceRead } from "../types/source";
import { usePageErrorHandler } from "./usePageErrorHandler";

export interface EnrichedRelation extends RelationRead {
  source?: SourceRead;
}

export function useEvidenceRelations(
  entityId: string | undefined,
  roleType: string | undefined,
  inference: InferenceRead | null | undefined,
): EnrichedRelation[] {
  const handlePageError = usePageErrorHandler();
  const [relations, setRelations] = useState<EnrichedRelation[]>([]);

  useEffect(() => {
    if (!entityId || !inference) {
      setRelations([]);
      return;
    }

    let isMounted = true;

    const loadRelations = async () => {
      try {
        const allRelations: RelationRead[] = [];
        if (inference.relations_by_kind) {
          Object.values(inference.relations_by_kind).forEach((items: unknown) => {
            if (Array.isArray(items)) {
              allRelations.push(...items);
            }
          });
        }

        const filteredRelations = roleType
          ? allRelations.filter((relation) =>
              relation.roles.some(
                (role) => role.entity_id === entityId && role.role_type === roleType,
              ),
            )
          : allRelations;

        if (isMounted) {
          setRelations(filteredRelations);
        }

        const enrichedRelations = await Promise.all(
          filteredRelations.map(async (relation) => {
            try {
              const source = await getSource(relation.source_id);
              return { ...relation, source };
            } catch {
              return relation;
            }
          }),
        );

        if (isMounted) {
          setRelations(enrichedRelations);
        }
      } catch (error) {
        if (isMounted) {
          setRelations([]);
          handlePageError(error, "Failed to load evidence");
        }
      }
    };

    void loadRelations();

    return () => {
      isMounted = false;
    };
  }, [entityId, handlePageError, inference, roleType]);

  return relations;
}

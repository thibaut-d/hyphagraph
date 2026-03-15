/**
 * EvidenceView (Hyperedges View)
 *
 * Scientific audit interface showing all evidence items (relations/hyperedges)
 * for an entity or a specific property type.
 *
 * Purpose (from UX.md):
 * - Enable scientific audit
 * - Show table of evidence items
 * - Display readable claims with direction indicators
 * - Show conditions and associated sources
 * - Allow filtering and sorting
 *
 * Navigation: PropertyDetailView -> "View All Related Evidence" -> This View
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";

import { EvidenceHeaderSection } from "../components/evidence/EvidenceHeaderSection";
import {
  EvidenceTableSection,
  type SortField,
  type SortOrder,
} from "../components/evidence/EvidenceTableSection";
import { useEntityInferenceDetail } from "../hooks/useEntityInferenceDetail";
import { useEvidenceRelations } from "../hooks/useEvidenceRelations";
import type { EvidenceItemRead } from "../types/inference";

function resolveRelationNotes(
  notes: string | Record<string, string> | null | undefined,
  language: string,
): string | null {
  if (!notes) {
    return null;
  }

  if (typeof notes === "string") {
    return notes;
  }

  return notes[language] || notes.en || Object.values(notes)[0] || null;
}

/**
 * EvidenceView Component
 *
 * Displays all evidence items (relations/hyperedges) for an entity:
 * - Filterable/sortable table of evidence
 * - Readable claims (relation kind)
 * - Direction indicators (supports/contradicts/neutral)
 * - Confidence scores
 * - Associated sources with links
 * - Optional filtering by roleType
 */
export function EvidenceView() {
  const { id, roleType } = useParams<{ id: string; roleType?: string }>();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const {
    data,
    error,
    loading: detailLoading,
  } = useEntityInferenceDetail(id, "Failed to load evidence");
  const entity = data?.entity ?? null;
  const inference = data?.inference ?? null;
  const { relations: fallbackRelations, sourceLoadFailures } = useEvidenceRelations(
    id,
    roleType,
    inference?.evidence_items ? null : inference,
  );
  const relations = (inference?.evidence_items
    ? inference.evidence_items.filter((relation: EvidenceItemRead) =>
        roleType
          ? relation.roles.some(
              (role) => role.entity_id === id && role.role_type === roleType,
            )
          : true,
      )
    : fallbackRelations);

  const [sortField, setSortField] = useState<SortField>("confidence");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Handle sorting
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  // Sort relations
  const sortedRelations = [...relations].sort((a, b) => {
    let comparison = 0;

    switch (sortField) {
      case "kind":
        comparison = (a.kind || "").localeCompare(b.kind || "");
        break;
      case "direction":
        comparison = (a.direction || "").localeCompare(b.direction || "");
        break;
      case "confidence":
        comparison = (a.confidence ?? 0) - (b.confidence ?? 0);
        break;
      case "source":
        comparison = (a.source?.title || "").localeCompare(b.source?.title || "");
        break;
    }

    return sortOrder === "asc" ? comparison : -comparison;
  });

  // Loading state
  if (detailLoading) {
    return (
      <Stack alignItems="center" mt={4}>
        <CircularProgress />
        <Typography variant="body2" color="text.secondary" mt={2}>
          {t("evidence.loading", "Loading evidence...")}
        </Typography>
      </Stack>
    );
  }

  // Error state
  if (error || (!entity && !detailLoading)) {
    return (
      <Alert severity="error">
        {error || t("common.error", "An error occurred")}
      </Alert>
    );
  }

  const entityLabel = entity.label || entity.slug;

  return (
    <Stack spacing={3}>
      <EvidenceHeaderSection
        entityId={id}
        entityLabel={entityLabel}
        roleType={roleType}
        relationCount={relations.length}
        onBack={() =>
          roleType
            ? navigate(`/entities/${id}/properties/${roleType}`)
            : navigate(`/entities/${id}`)
        }
      />

      <EvidenceTableSection
        entityId={id}
        entityLabel={entityLabel}
        language={i18n.language}
        roleType={roleType}
        relations={sortedRelations}
        sortField={sortField}
        sortOrder={sortOrder}
        onSort={handleSort}
        resolveNotes={resolveRelationNotes}
      />

      {sourceLoadFailures.length > 0 && (
        <Alert severity="warning">
          <Typography variant="body2">
            {t(
              "evidence.partial_source_warning",
              "Some source details could not be loaded. The evidence rows are still shown, but some source metadata may be missing."
            )}
          </Typography>
        </Alert>
      )}

      <Alert severity="info">
        <Typography variant="body2">
          {t(
            "evidence.audit_note",
            "INFO: This view provides complete transparency into all evidence items. Every relation shown here contributes to the computed inferences you see elsewhere in the system."
          )}
        </Typography>
      </Alert>
    </Stack>
  );
}

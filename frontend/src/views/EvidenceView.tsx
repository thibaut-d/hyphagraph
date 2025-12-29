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
 * Navigation: PropertyDetailView → "View All Related Evidence" → This View
 */

import { useEffect, useState } from "react";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Typography,
  Paper,
  Stack,
  CircularProgress,
  Alert,
  Box,
  Breadcrumbs,
  Link,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Chip,
  Button,
  IconButton,
  Tooltip,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import HelpIcon from "@mui/icons-material/Help";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";

import { getEntity, EntityRead } from "../api/entities";
import { getInferenceForEntity } from "../api/inferences";
import { getSource, SourceRead } from "../api/sources";
import { RelationRead } from "../types/relation";
import { resolveLabel } from "../utils/i18nLabel";

type SortField = "kind" | "direction" | "confidence" | "source";
type SortOrder = "asc" | "desc";

interface EnrichedRelation extends RelationRead {
  source?: SourceRead;
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
  const { entityId, roleType } = useParams<{ entityId: string; roleType?: string }>();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const [entity, setEntity] = useState<EntityRead | null>(null);
  const [relations, setRelations] = useState<EnrichedRelation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [sortField, setSortField] = useState<SortField>("confidence");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Fetch entity and relations
  useEffect(() => {
    if (!entityId) {
      setError("Missing entity ID");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([
      getEntity(entityId),
      getInferenceForEntity(entityId),
    ])
      .then(async ([entityData, inferenceData]) => {
        setEntity(entityData);

        // Extract all relations from inference data
        const allRelations: RelationRead[] = [];
        if (inferenceData && inferenceData.relations_by_kind) {
          Object.values(inferenceData.relations_by_kind).forEach((rels: any) => {
            if (Array.isArray(rels)) {
              allRelations.push(...rels);
            }
          });
        }

        // Filter by roleType if specified
        const filteredRelations = roleType
          ? allRelations.filter((rel) =>
              rel.roles.some(
                (role) => role.entity_id === entityId && role.role_type === roleType
              )
            )
          : allRelations;

        // Enrich with source data
        const enrichedRelations = await Promise.all(
          filteredRelations.map(async (rel) => {
            try {
              const source = await getSource(rel.source_id);
              return { ...rel, source };
            } catch (err) {
              console.error(`Failed to load source ${rel.source_id}:`, err);
              return rel;
            }
          })
        );

        setRelations(enrichedRelations);
      })
      .catch((err) => {
        console.error("Failed to load evidence:", err);
        setError(err.message || "Failed to load evidence");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [entityId, roleType]);

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
        comparison = a.kind.localeCompare(b.kind);
        break;
      case "direction":
        comparison = (a.direction || "").localeCompare(b.direction || "");
        break;
      case "confidence":
        comparison = a.confidence - b.confidence;
        break;
      case "source":
        comparison = (a.source?.title || "").localeCompare(b.source?.title || "");
        break;
    }

    return sortOrder === "asc" ? comparison : -comparison;
  });

  // Loading state
  if (loading) {
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
  if (error || !entity) {
    return (
      <Alert severity="error">
        {error || t("common.error", "An error occurred")}
      </Alert>
    );
  }

  const entityLabel = resolveLabel(entity.label, entity.label_i18n, i18n.language);

  // Direction chip helper
  const getDirectionChip = (direction: string) => {
    switch (direction) {
      case "supports":
        return (
          <Chip
            icon={<CheckCircleIcon />}
            label={t("evidence.supports", "Supports")}
            color="success"
            size="small"
          />
        );
      case "contradicts":
        return (
          <Chip
            icon={<CancelIcon />}
            label={t("evidence.contradicts", "Contradicts")}
            color="error"
            size="small"
          />
        );
      default:
        return (
          <Chip
            icon={<HelpIcon />}
            label={t("evidence.neutral", "Neutral")}
            color="default"
            size="small"
            variant="outlined"
          />
        );
    }
  };

  return (
    <Stack spacing={3}>
      {/* Breadcrumbs */}
      <Breadcrumbs>
        <Link component={RouterLink} to="/entities" underline="hover">
          {t("menu.entities", "Entities")}
        </Link>
        <Link component={RouterLink} to={`/entities/${entityId}`} underline="hover">
          {entityLabel}
        </Link>
        {roleType && (
          <Link
            component={RouterLink}
            to={`/entities/${entityId}/properties/${roleType}`}
            underline="hover"
          >
            {roleType}
          </Link>
        )}
        <Typography color="text.primary">
          {t("evidence.title", "Evidence")}
        </Typography>
      </Breadcrumbs>

      {/* Back button */}
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() =>
            roleType
              ? navigate(`/entities/${entityId}/properties/${roleType}`)
              : navigate(`/entities/${entityId}`)
          }
          variant="outlined"
          size="small"
        >
          {t("common.back", "Back")}
        </Button>
      </Box>

      {/* Header */}
      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h4" component="h1">
            {roleType
              ? t("evidence.header_filtered", "Evidence for {{roleType}}", { roleType })
              : t("evidence.header_all", "All Evidence")}
          </Typography>
          <Typography variant="h6" color="text.secondary">
            {entityLabel}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t(
              "evidence.description",
              "Complete audit trail of all evidence items (hyperedges) involving this entity. Each row represents a relation from a source document."
            )}
          </Typography>
          <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
            <Chip
              label={t("evidence.count", "{{count}} evidence items", {
                count: relations.length,
              })}
              color="primary"
              variant="outlined"
            />
          </Box>
        </Stack>
      </Paper>

      {/* Evidence Table */}
      {relations.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={sortField === "kind"}
                    direction={sortField === "kind" ? sortOrder : "asc"}
                    onClick={() => handleSort("kind")}
                  >
                    <strong>{t("evidence.table.claim", "Claim / Relation Kind")}</strong>
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === "direction"}
                    direction={sortField === "direction" ? sortOrder : "asc"}
                    onClick={() => handleSort("direction")}
                  >
                    <strong>{t("evidence.table.direction", "Direction")}</strong>
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === "confidence"}
                    direction={sortField === "confidence" ? sortOrder : "asc"}
                    onClick={() => handleSort("confidence")}
                  >
                    <strong>{t("evidence.table.confidence", "Confidence")}</strong>
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <strong>{t("evidence.table.roles", "Roles")}</strong>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === "source"}
                    direction={sortField === "source" ? sortOrder : "asc"}
                    onClick={() => handleSort("source")}
                  >
                    <strong>{t("evidence.table.source", "Source")}</strong>
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <strong>{t("evidence.table.notes", "Notes")}</strong>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedRelations.map((relation) => (
                <TableRow key={relation.id} hover>
                  {/* Claim/Kind */}
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {relation.kind}
                    </Typography>
                  </TableCell>

                  {/* Direction */}
                  <TableCell>{getDirectionChip(relation.direction)}</TableCell>

                  {/* Confidence */}
                  <TableCell>
                    <Chip
                      label={`${Math.round(relation.confidence * 100)}%`}
                      size="small"
                      color={
                        relation.confidence > 0.7
                          ? "success"
                          : relation.confidence > 0.4
                          ? "warning"
                          : "error"
                      }
                    />
                  </TableCell>

                  {/* Roles */}
                  <TableCell>
                    <Stack spacing={0.5}>
                      {relation.roles.map((role, idx) => (
                        <Box key={idx} sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                          <Typography variant="caption" color="text.secondary">
                            {role.role_type}:
                          </Typography>
                          <Link
                            component={RouterLink}
                            to={`/entities/${role.entity_id}`}
                            variant="caption"
                            underline="hover"
                          >
                            {role.entity_id === entityId ? entityLabel : role.entity_id}
                          </Link>
                        </Box>
                      ))}
                    </Stack>
                  </TableCell>

                  {/* Source */}
                  <TableCell>
                    {relation.source ? (
                      <Box>
                        <Link
                          component={RouterLink}
                          to={`/sources/${relation.source_id}`}
                          variant="body2"
                          sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
                        >
                          {relation.source.title}
                          <OpenInNewIcon fontSize="small" />
                        </Link>
                        {relation.source.authors && relation.source.authors.length > 0 && (
                          <Typography variant="caption" color="text.secondary">
                            {relation.source.authors.slice(0, 2).join(", ")}
                            {relation.source.authors.length > 2 && " et al."}
                            {relation.source.year && ` (${relation.source.year})`}
                          </Typography>
                        )}
                      </Box>
                    ) : (
                      <Link
                        component={RouterLink}
                        to={`/sources/${relation.source_id}`}
                        variant="body2"
                      >
                        View Source
                      </Link>
                    )}
                  </TableCell>

                  {/* Notes */}
                  <TableCell>
                    {relation.notes ? (
                      <Tooltip title={relation.notes} arrow>
                        <IconButton size="small">
                          <HelpIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        -
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Alert severity="info">
          <Typography variant="body1" gutterBottom>
            {t("evidence.no_data.title", "No evidence found")}
          </Typography>
          <Typography variant="body2">
            {roleType
              ? t(
                  "evidence.no_data.filtered",
                  "No evidence items found for this specific property type."
                )
              : t(
                  "evidence.no_data.all",
                  "This entity has no associated relations yet. Add sources and relations to build the evidence base."
                )}
          </Typography>
        </Alert>
      )}

      {/* Scientific Honesty Note */}
      <Alert severity="info">
        <Typography variant="body2">
          {t(
            "evidence.audit_note",
            "ℹ️ This view provides complete transparency into all evidence items. Every relation shown here contributes to the computed inferences you see elsewhere in the system."
          )}
        </Typography>
      </Alert>
    </Stack>
  );
}

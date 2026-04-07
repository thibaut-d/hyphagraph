import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Chip,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import type { RelationRead } from "../../types/relation";

interface SourceRelationsSectionProps {
  relations: RelationRead[];
  relationsError: string | null;
  highlightedRelationId?: string | null;
  onDeleteRelation: (relation: RelationRead) => void;
}

export function SourceRelationsSection({
  relations,
  relationsError,
  highlightedRelationId,
  onDeleteRelation,
}: SourceRelationsSectionProps) {
  const { t } = useTranslation();
  const [directionFilter, setDirectionFilter] = useState<"all" | "supports" | "contradicts" | "other">("all");
  const [expandedKinds, setExpandedKinds] = useState<string[]>([]);
  const hasRelations = relations.length > 0;
  const highlightedRelation = highlightedRelationId
    ? relations.find((relation) => relation.id === highlightedRelationId) ?? null
    : null;

  const resolveNotes = (notes: string | Record<string, string> | null | undefined) => {
    if (!notes) {
      return null;
    }

    if (typeof notes === "string") {
      return notes;
    }

    return notes.en || Object.values(notes)[0] || null;
  };

  const formatRoleTypeLabel = (roleType: string) =>
    roleType
      .split(/[_-]+/)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");

  const getDirectionBucket = (relation: RelationRead): "supports" | "contradicts" | "other" => {
    if (relation.direction === "supports") {
      return "supports";
    }
    if (relation.direction === "contradicts") {
      return "contradicts";
    }
    return "other";
  };

  const supportsCount = relations.filter((relation) => getDirectionBucket(relation) === "supports").length;
  const contradictsCount = relations.filter((relation) => getDirectionBucket(relation) === "contradicts").length;
  const otherCount = relations.length - supportsCount - contradictsCount;
  const filteredRelations = relations.filter((relation) =>
    directionFilter === "all" ? true : getDirectionBucket(relation) === directionFilter,
  );

  const groupedRelations = filteredRelations.reduce<Record<string, RelationRead[]>>((groups, relation) => {
    const key = relation.kind || t("sources.unknown_relation_kind", "Uncategorized");
    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(relation);
    return groups;
  }, {});

  const orderedKinds = Object.keys(groupedRelations).sort((a, b) => a.localeCompare(b));

  useEffect(() => {
    if (relations.length === 0) {
      setExpandedKinds([]);
      return;
    }

    const availableKinds = Array.from(
      new Set(relations.map((relation) => relation.kind || t("sources.unknown_relation_kind", "Uncategorized"))),
    );

    setExpandedKinds((current) => {
      if (current.length === 0) {
        return availableKinds;
      }

      const next = current.filter((kind) => availableKinds.includes(kind));
      return next.length > 0 ? next : availableKinds;
    });
  }, [relations, t]);

  useEffect(() => {
    if (!highlightedRelation) {
      return;
    }

    const highlightedKind =
      highlightedRelation.kind || t("sources.unknown_relation_kind", "Uncategorized");

    setExpandedKinds((current) =>
      current.includes(highlightedKind) ? current : [...current, highlightedKind],
    );

    const highlightedDirection = getDirectionBucket(highlightedRelation);
    setDirectionFilter((current) => (current === "all" || current === highlightedDirection ? current : "all"));
  }, [highlightedRelation, t]);

  const toggleGroup = (kind: string) => {
    setExpandedKinds((current) =>
      current.includes(kind) ? current.filter((item) => item !== kind) : [...current, kind],
    );
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5">{t("sources.linked_relations_entities", "Linked relations and entities")}</Typography>
        {hasRelations && (
          <Chip label={`${relations.length} ${t("sources.relations_count", "relations")}`} color="primary" size="small" />
        )}
      </Box>

      <Divider sx={{ mb: 2 }} />

      {relationsError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {relationsError}
        </Alert>
      )}

      {highlightedRelation && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {t(
            "sources.highlighted_relation",
            {
              defaultValue: "Highlighted evidence target: {{kind}}",
              kind: highlightedRelation.kind || highlightedRelation.id,
            },
          )}
        </Alert>
      )}

      {relations.length === 0 && !relationsError ? (
        <Alert severity="info">
          {t("sources.no_relations", "No relations yet. Extract knowledge from this source to create relations.")}
        </Alert>
      ) : relations.length > 0 ? (
        <Stack spacing={2}>
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t("sources.relation_summary", "Summary")}
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              <Chip label={`${supportsCount} ${t("evidence.supports", "Supports")}`} color="success" size="small" />
              <Chip label={`${contradictsCount} ${t("evidence.contradicts", "Contradicts")}`} color="error" size="small" />
              <Chip label={`${otherCount} ${t("evidence.neutral", "Neutral")}`} variant="outlined" size="small" />
            </Box>
          </Box>

          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t("sources.filter_relations", "Filter relations")}
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              <Chip
                label={t("common.all", "All")}
                color={directionFilter === "all" ? "primary" : "default"}
                variant={directionFilter === "all" ? "filled" : "outlined"}
                onClick={() => setDirectionFilter("all")}
              />
              <Chip
                label={t("evidence.supports", "Supports")}
                color={directionFilter === "supports" ? "success" : "default"}
                variant={directionFilter === "supports" ? "filled" : "outlined"}
                onClick={() => setDirectionFilter("supports")}
              />
              <Chip
                label={t("evidence.contradicts", "Contradicts")}
                color={directionFilter === "contradicts" ? "error" : "default"}
                variant={directionFilter === "contradicts" ? "filled" : "outlined"}
                onClick={() => setDirectionFilter("contradicts")}
              />
              <Chip
                label={t("evidence.neutral", "Neutral")}
                color={directionFilter === "other" ? "primary" : "default"}
                variant={directionFilter === "other" ? "filled" : "outlined"}
                onClick={() => setDirectionFilter("other")}
              />
            </Box>
          </Box>

          {filteredRelations.length === 0 ? (
            <Alert severity="info">
              {t("sources.no_filtered_relations", "No relations match the current filter.")}
            </Alert>
          ) : (
            orderedKinds.map((kind) => {
              const relationsInGroup = groupedRelations[kind];
              const supportsInGroup = relationsInGroup.filter((relation) => getDirectionBucket(relation) === "supports").length;
              const contradictsInGroup = relationsInGroup.filter((relation) => getDirectionBucket(relation) === "contradicts").length;
              const otherInGroup = relationsInGroup.length - supportsInGroup - contradictsInGroup;

              return (
                <Accordion
                  key={kind}
                  expanded={expandedKinds.includes(kind)}
                  onChange={() => toggleGroup(kind)}
                  disableGutters
                >
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1, width: "100%" }}>
                      <Typography sx={{ fontWeight: 600 }}>{kind}</Typography>
                      <Chip label={`${relationsInGroup.length}`} size="small" color="primary" />
                      {supportsInGroup > 0 && <Chip label={`${supportsInGroup} ${t("evidence.supports", "Supports")}`} size="small" color="success" />}
                      {contradictsInGroup > 0 && <Chip label={`${contradictsInGroup} ${t("evidence.contradicts", "Contradicts")}`} size="small" color="error" />}
                      {otherInGroup > 0 && <Chip label={`${otherInGroup} ${t("evidence.neutral", "Neutral")}`} size="small" variant="outlined" />}
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails sx={{ px: 0 }}>
                    <List sx={{ pt: 0 }}>
                      {relationsInGroup.map((relation) => {
                        const isHighlighted = relation.id === highlightedRelationId;
                        const resolvedNotes = resolveNotes(relation.notes);

                        return (
                          <ListItem
                            key={relation.id}
                            id={`relation-${relation.id}`}
                            data-highlighted={isHighlighted ? "true" : "false"}
                            sx={{
                              borderLeft: 3,
                              borderColor:
                                isHighlighted
                                  ? "primary.main"
                                  : relation.direction === "supports"
                                    ? "success.main"
                                    : relation.direction === "contradicts"
                                      ? "error.main"
                                      : "grey.400",
                              mb: 1,
                              bgcolor: isHighlighted ? "action.selected" : "background.default",
                            }}
                            secondaryAction={
                              <Box sx={{ display: "flex", gap: 0.5 }}>
                                <IconButton
                                  component={RouterLink}
                                  to={`/relations/${relation.id}/edit`}
                                  edge="end"
                                  size="small"
                                  title={t("common.edit", "Edit")}
                                >
                                  <EditIcon fontSize="small" />
                                </IconButton>
                                <IconButton
                                  edge="end"
                                  size="small"
                                  color="error"
                                  onClick={() => onDeleteRelation(relation)}
                                  title={t("common.delete", "Delete")}
                                >
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Box>
                            }
                          >
                            <ListItemText
                              primary={
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                  <Link
                                    component={RouterLink}
                                    to={`/relations/${relation.id}`}
                                    underline="hover"
                                    color="inherit"
                                    sx={{ fontWeight: 500 }}
                                  >
                                    {relation.kind}
                                  </Link>
                                  <Chip
                                    label={relation.direction}
                                    size="small"
                                    color={relation.direction === "supports" ? "success" : relation.direction === "contradicts" ? "error" : "default"}
                                    sx={{ fontSize: "0.7rem" }}
                                  />
                                </Box>
                              }
                              secondary={
                                <>
                                  {isHighlighted && (
                                    <>
                                      <Typography
                                        component="span"
                                        variant="caption"
                                        color="primary.main"
                                        sx={{ display: "block", mb: 0.5, fontWeight: 600 }}
                                      >
                                        {t("sources.highlighted_relation_row", "Requested from evidence trace")}
                                      </Typography>
                                      {resolvedNotes && (
                                        <Typography
                                          component="span"
                                          variant="body2"
                                          color="text.primary"
                                          sx={{ display: "block", mb: 0.75 }}
                                        >
                                          {resolvedNotes}
                                        </Typography>
                                      )}
                                    </>
                                  )}
                                  <Box component="span" sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                                    {relation.roles.map((role, index) => {
                                      const entityLabel = role.entity_slug || role.entity_id;

                                      return (
                                        <Box
                                          key={index}
                                          component="span"
                                          sx={{ display: "inline-flex", alignItems: "baseline", gap: 0.5 }}
                                        >
                                          <Link component={RouterLink} to={`/entities/${role.entity_slug || role.entity_id}`}>
                                            {entityLabel}
                                          </Link>
                                          <Typography component="span" variant="caption" color="text.secondary">
                                            ({formatRoleTypeLabel(role.role_type)})
                                          </Typography>
                                        </Box>
                                      );
                                    })}
                                  </Box>
                                </>
                              }
                            />
                          </ListItem>
                        );
                      })}
                    </List>
                  </AccordionDetails>
                </Accordion>
              );
            })
          )}
        </Stack>
      ) : null}
    </Paper>
  );
}

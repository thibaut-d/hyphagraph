/**
 * ExtractionPreview component
 *
 * Displays extraction results with entity linking suggestions and allows
 * user to review and approve entities/relations before saving to graph.
 */
import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Paper,
  Typography,
  Stack,
  Chip,
  Button,
  Alert,
  Divider,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import {
  CheckCircle as CheckCircleIcon,
  Link as LinkIcon,
  AddCircle as AddCircleIcon,
  RemoveCircle as RemoveCircleIcon,
  Save as SaveIcon,
  ExpandMore as ExpandMoreIcon,
  Article as ArticleIcon,
} from "@mui/icons-material";
import type {
  DocumentExtractionPreview,
  EntityLinkingDecision,
  SaveExtractionRequest,
  SaveExtractionResult,
} from "../types/extraction";
import { saveExtraction } from "../api/extraction";
import { EntityLinkingSuggestions } from "./EntityLinkingSuggestions";
import { ExtractedRelationsList } from "./ExtractedRelationsList";
import { getRelationKey } from "../utils/extractionRelation";

interface ExtractionPreviewProps {
  preview: DocumentExtractionPreview;
  onSaveComplete: (result: SaveExtractionResult) => void;
  onCancel?: () => void;
}

export const ExtractionPreview: React.FC<ExtractionPreviewProps> = ({
  preview,
  onSaveComplete,
  onCancel,
}) => {
  const [entityDecisions, setEntityDecisions] = useState<
    Record<string, EntityLinkingDecision>
  >(() => {
    // Initialize decisions based on link suggestions
    const decisions: Record<string, EntityLinkingDecision> = {};

    preview.link_suggestions.forEach((suggestion) => {
      if (suggestion.match_type === "exact" || suggestion.match_type === "synonym") {
        // Auto-link high-confidence matches
        decisions[suggestion.extracted_slug] = {
          extracted_slug: suggestion.extracted_slug,
          action: "link",
          linked_entity_id: suggestion.matched_entity_id || undefined,
        };
      } else {
        // Default to creating new entities
        decisions[suggestion.extracted_slug] = {
          extracted_slug: suggestion.extracted_slug,
          action: "create",
        };
      }
    });

    return decisions;
  });

  const [selectedRelations, setSelectedRelations] = useState<Set<string>>(
    new Set(preview.relations.map(getRelationKey))
  );

  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      // Build save request from user decisions
      const entitiesToCreate = preview.entities.filter(
        (e) => entityDecisions[e.slug]?.action === "create"
      );

      const entityLinks: Record<string, string> = {};
      Object.values(entityDecisions).forEach((decision) => {
        if (decision.action === "link" && decision.linked_entity_id) {
          entityLinks[decision.extracted_slug] = decision.linked_entity_id;
        }
      });

      const relationsToCreate = preview.relations.filter((r) =>
        selectedRelations.has(getRelationKey(r))
      );

      const request: SaveExtractionRequest = {
        entities_to_create: entitiesToCreate,
        entity_links: entityLinks,
        relations_to_create: relationsToCreate,
      };

      const result = await saveExtraction(preview.source_id, request);
      onSaveComplete(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("extraction_preview.save_error"));
    } finally {
      setSaving(false);
    }
  };

  const handleEntityDecisionChange = (slug: string, decision: EntityLinkingDecision) => {
    setEntityDecisions((prev) => ({
      ...prev,
      [slug]: decision,
    }));
  };

  const handleRelationToggle = (relationKey: string) => {
    setSelectedRelations((prev) => {
      const next = new Set(prev);
      if (next.has(relationKey)) {
        next.delete(relationKey);
      } else {
        next.add(relationKey);
      }
      return next;
    });
  };

  const stats = {
    toCreate: Object.values(entityDecisions).filter((d) => d.action === "create").length,
    toLink: Object.values(entityDecisions).filter((d) => d.action === "link").length,
    toSkip: Object.values(entityDecisions).filter((d) => d.action === "skip").length,
    relationsSelected: selectedRelations.size,
  };

  // Auto-accept logic: If all entities are high-confidence matches, show quick save option
  const allHighConfidence =
    preview.link_suggestions.every((s) => s.match_type === "exact" || s.match_type === "synonym") &&
    preview.entities.every((e) => e.confidence === "high");

  const hasDecisions = stats.toCreate > 0 || stats.toLink > 0;

  return (
    <Paper sx={{ p: 3, border: 2, borderColor: "primary.main" }}>
      <Stack spacing={3}>
        {/* Header */}
        <Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
            <CheckCircleIcon color="success" />
            <Typography variant="h5">{t("extraction_preview.title")}</Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {allHighConfidence ? (
              <>
                <strong>{t("extraction_preview.high_confidence_bold")}</strong>{" "}
                {t("extraction_preview.high_confidence_rest")}
              </>
            ) : (
              <>{t("extraction_preview.review_msg")}</>
            )}
          </Typography>
        </Box>

        {/* Stats */}
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <Chip
            icon={<AddCircleIcon />}
            label={t("extraction_preview.new_entities", { count: stats.toCreate })}
            color="success"
            variant="outlined"
          />
          <Chip
            icon={<LinkIcon />}
            label={t("extraction_preview.linked_entities", { count: stats.toLink })}
            color="info"
            variant="outlined"
          />
          {stats.toSkip > 0 && (
            <Chip
              icon={<RemoveCircleIcon />}
              label={t("extraction_preview.skipped_entities", { count: stats.toSkip })}
              color="warning"
              variant="outlined"
            />
          )}
          <Chip
            icon={<CheckCircleIcon />}
            label={t("extraction_preview.relations", { count: stats.relationsSelected })}
            color="primary"
            variant="outlined"
          />
        </Box>

        <Divider />

        {/* Extracted Text (Optional) */}
        {preview.extracted_text && (
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <ArticleIcon />
                <Typography variant="h6">
                  {t("extraction_preview.extracted_text", { count: preview.extracted_text.length })}
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Box
                sx={{
                  maxHeight: 400,
                  overflowY: "auto",
                  p: 2,
                  bgcolor: "grey.50",
                  borderRadius: 1,
                  whiteSpace: "pre-wrap",
                  fontFamily: "monospace",
                  fontSize: "0.875rem",
                }}
              >
                {preview.extracted_text}
              </Box>
            </AccordionDetails>
          </Accordion>
        )}

        {/* Entity Linking Suggestions */}
        <Box>
          <Typography variant="h6" gutterBottom>
            {t("extraction_preview.entities_section", { count: preview.entity_count })}
          </Typography>
          <EntityLinkingSuggestions
            entities={preview.entities}
            linkSuggestions={preview.link_suggestions}
            decisions={entityDecisions}
            onDecisionChange={handleEntityDecisionChange}
          />
        </Box>

        <Divider />

        {/* Relations */}
        <Box>
          <Typography variant="h6" gutterBottom>
            {t("extraction_preview.relations_section", { count: preview.relation_count })}
          </Typography>
          <ExtractedRelationsList
            relations={preview.relations}
            selectedRelations={selectedRelations}
            onToggle={handleRelationToggle}
          />
        </Box>

        {error && (
          <Alert severity="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Help message when all entities are skipped */}
        {stats.toCreate === 0 && stats.toLink === 0 && !saving && (
          <Alert severity="info">
            {t("extraction_preview.no_entities_alert")}
          </Alert>
        )}

        {/* Quick Save for High-Confidence Extractions */}
        {allHighConfidence && (
          <Alert severity="success" sx={{ bgcolor: "success.50" }}>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                  {t("extraction_preview.all_validated")}
                </Typography>
                <Typography variant="caption">
                  {t("extraction_preview.quick_save_stats", { create: stats.toCreate, link: stats.toLink, relations: stats.relationsSelected })}
                </Typography>
              </Box>
              <Button
                variant="contained"
                color="success"
                size="large"
                startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                onClick={handleSave}
                disabled={saving || !hasDecisions}
                sx={{ minWidth: 180, fontWeight: 600 }}
              >
                {saving ? t("extraction_preview.saving") : t("extraction_preview.quick_save")}
              </Button>
            </Box>
          </Alert>
        )}

        {/* Actions */}
        <Box sx={{ display: "flex", gap: 2, justifyContent: "space-between", alignItems: "center" }}>
          <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
            {hasDecisions
              ? t("extraction_preview.review_guidance")
              : t("extraction_preview.all_skipped")}
          </Typography>
          <Box sx={{ display: "flex", gap: 2 }}>
            {onCancel && (
              <Button onClick={onCancel} disabled={saving} variant="outlined">
                {t("common.cancel")}
              </Button>
            )}
            {!allHighConfidence && (
              <Button
                variant="contained"
                size="large"
                startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
                onClick={handleSave}
                disabled={saving || !hasDecisions}
                sx={{ minWidth: 180 }}
              >
                {saving ? t("extraction_preview.saving") : t("extraction_preview.save_to_graph")}
              </Button>
            )}
          </Box>
        </Box>
      </Stack>
    </Paper>
  );
};

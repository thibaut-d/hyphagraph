/**
 * ExtractionPreview component
 *
 * Displays extraction results with entity linking suggestions and allows
 * user to review and approve entities/relations before saving to graph.
 */
import React, { useState } from "react";
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
    new Set(preview.relations.map((r) => `${r.subject_slug}-${r.relation_type}-${r.object_slug}`))
  );

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        selectedRelations.has(`${r.subject_slug}-${r.relation_type}-${r.object_slug}`)
      );

      const request: SaveExtractionRequest = {
        source_id: preview.source_id,
        entities_to_create: entitiesToCreate,
        entity_links: entityLinks,
        relations_to_create: relationsToCreate,
      };

      const result = await saveExtraction(preview.source_id, request);
      onSaveComplete(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save extraction");
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

  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Box>
          <Typography variant="h5" gutterBottom>
            Extraction Preview
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Review extracted entities and relations before saving to the knowledge graph.
          </Typography>
        </Box>

        {/* Stats */}
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <Chip
            icon={<AddCircleIcon />}
            label={`${stats.toCreate} new entities`}
            color="success"
            variant="outlined"
          />
          <Chip
            icon={<LinkIcon />}
            label={`${stats.toLink} linked entities`}
            color="info"
            variant="outlined"
          />
          {stats.toSkip > 0 && (
            <Chip
              icon={<RemoveCircleIcon />}
              label={`${stats.toSkip} skipped entities`}
              color="warning"
              variant="outlined"
            />
          )}
          <Chip
            icon={<CheckCircleIcon />}
            label={`${stats.relationsSelected} relations`}
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
                  Extracted Text ({preview.extracted_text.length.toLocaleString()} characters)
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
            Entities ({preview.entity_count})
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
            Relations ({preview.relation_count})
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
            No entities selected. Please select at least one entity to create or link before saving.
          </Alert>
        )}

        {/* Actions */}
        <Box sx={{ display: "flex", gap: 2, justifyContent: "flex-end" }}>
          {onCancel && (
            <Button onClick={onCancel} disabled={saving}>
              Cancel
            </Button>
          )}
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
            onClick={handleSave}
            disabled={saving || (stats.toCreate === 0 && stats.toLink === 0)}
          >
            {saving ? "Saving..." : "Save to Graph"}
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
};

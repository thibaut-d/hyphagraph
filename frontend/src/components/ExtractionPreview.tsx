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
} from "@mui/material";
import {
  CheckCircle as CheckCircleIcon,
  Link as LinkIcon,
  AddCircle as AddCircleIcon,
  RemoveCircle as RemoveCircleIcon,
  Save as SaveIcon,
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
            <Typography variant="h5">Extraction Complete!</Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {allHighConfidence ? (
              <>
                <strong>✓ High-confidence extraction detected.</strong> All entities have exact or synonym matches.
                You can quick-save or review details below.
              </>
            ) : (
              <>Review extracted entities and relations before saving to the knowledge graph.</>
            )}
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

        {/* Quick Save for High-Confidence Extractions */}
        {allHighConfidence && (
          <Alert severity="success" sx={{ bgcolor: "success.50" }}>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                  ✓ All entities validated with high confidence
                </Typography>
                <Typography variant="caption">
                  {stats.toCreate} new entities • {stats.toLink} linked entities • {stats.relationsSelected} relations
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
                {saving ? "Saving..." : "Quick Save ✓"}
              </Button>
            </Box>
          </Alert>
        )}

        {/* Actions */}
        <Box sx={{ display: "flex", gap: 2, justifyContent: "space-between", alignItems: "center" }}>
          <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
            {hasDecisions
              ? "Review entities and relations above, then save to add them to the knowledge graph."
              : "All entities skipped. Adjust decisions above to enable saving."}
          </Typography>
          <Box sx={{ display: "flex", gap: 2 }}>
            {onCancel && (
              <Button onClick={onCancel} disabled={saving} variant="outlined">
                Cancel
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
                {saving ? "Saving..." : "Save to Graph"}
              </Button>
            )}
          </Box>
        </Box>
      </Stack>
    </Paper>
  );
};

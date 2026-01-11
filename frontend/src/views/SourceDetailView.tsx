import { useEffect, useState } from "react";
import { useParams, Link as RouterLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Paper,
  Typography,
  Stack,
  Divider,
  List,
  ListItem,
  ListItemText,
  Link,
  IconButton,
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Alert,
  CircularProgress,
  Chip,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import LinkIcon from "@mui/icons-material/Link";
import SmartToyIcon from "@mui/icons-material/SmartToy";

import { getSource, deleteSource } from "../api/sources";
import { listRelationsBySource, deleteRelation } from "../api/relations";
import { uploadAndExtract, extractFromUrl } from "../api/extraction";
import { SourceRead } from "../types/source";
import { RelationRead } from "../types/relation";
import { invalidateSourceFilterCache } from "../utils/cacheUtils";
import { DocumentExtractionPreview, SaveExtractionResult } from "../types/extraction";
import { ExtractionPreview } from "../components/ExtractionPreview";
import { UrlExtractionDialog } from "../components/UrlExtractionDialog";

export function SourceDetailView() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [source, setSource] = useState<SourceRead | null>(null);
  const [relations, setRelations] = useState<RelationRead[]>([]);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [relationToDelete, setRelationToDelete] = useState<RelationRead | null>(null);
  const [deleteRelationDialogOpen, setDeleteRelationDialogOpen] = useState(false);
  const [deletingRelation, setDeletingRelation] = useState(false);

  // Extraction workflow state
  const [autoExtracting, setAutoExtracting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [extractionPreview, setExtractionPreview] = useState<DocumentExtractionPreview | null>(null);
  const [saveResult, setSaveResult] = useState<SaveExtractionResult | null>(null);

  // URL extraction state
  const [urlDialogOpen, setUrlDialogOpen] = useState(false);
  const [urlExtracting, setUrlExtracting] = useState(false);

  useEffect(() => {
    if (!id) return;

    getSource(id).then(setSource);
    listRelationsBySource(id).then(setRelations);
  }, [id]);

  const handleDelete = async () => {
    if (!id) return;

    setDeleting(true);
    try {
      await deleteSource(id);

      // Invalidate filter options cache since we deleted a source
      invalidateSourceFilterCache();

      navigate("/sources");
    } catch (error) {
      console.error("Failed to delete source:", error);
      setDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

  const handleDeleteRelation = async () => {
    if (!relationToDelete || !id) return;

    setDeletingRelation(true);
    try {
      await deleteRelation(relationToDelete.id);
      // Refresh relations list
      const updatedRelations = await listRelationsBySource(id);
      setRelations(updatedRelations);
      setDeleteRelationDialogOpen(false);
      setRelationToDelete(null);
    } catch (error) {
      console.error("Failed to delete relation:", error);
    } finally {
      setDeletingRelation(false);
    }
  };

  const openDeleteRelationDialog = (relation: RelationRead) => {
    setRelationToDelete(relation);
    setDeleteRelationDialogOpen(true);
  };

  // ============================================================================
  // ONE-CLICK AUTO-EXTRACTION (Smart Workflow)
  // ============================================================================

  const handleAutoExtract = async () => {
    if (!id || !source) return;

    setAutoExtracting(true);
    setUploadError(null);
    setSaveResult(null);

    try {
      // Smart detection: use source URL for extraction
      if (source.url) {
        const preview = await extractFromUrl(id, source.url);
        setExtractionPreview(preview);
      } else {
        // No URL available - prompt for upload
        setUploadError("No URL available. Please upload a document or provide a URL.");
        setAutoExtracting(false);
      }
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Failed to auto-extract knowledge");
      setAutoExtracting(false);
    } finally {
      setAutoExtracting(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !id) return;

    setUploading(true);
    setUploadError(null);
    setSaveResult(null);

    try {
      const preview = await uploadAndExtract(id, file);
      setExtractionPreview(preview);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Failed to upload and extract");
    } finally {
      setUploading(false);
      // Clear file input
      event.target.value = "";
    }
  };

  const handleSaveComplete = async (result: SaveExtractionResult) => {
    setSaveResult(result);
    setExtractionPreview(null);

    // Refresh relations list
    if (id) {
      const updatedRelations = await listRelationsBySource(id);
      setRelations(updatedRelations);
    }
  };

  const handleCancelExtraction = () => {
    setExtractionPreview(null);
    setUploadError(null);
  };

  const handleUrlExtraction = async (url: string) => {
    if (!id) return;

    setUrlExtracting(true);
    setUploadError(null);
    setSaveResult(null);

    try {
      const preview = await extractFromUrl(id, url);
      setExtractionPreview(preview);
      setUrlDialogOpen(false);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Failed to extract from URL");
      throw error; // Re-throw to let dialog handle error display
    } finally {
      setUrlExtracting(false);
    }
  };

  if (!source) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  const hasUrl = !!source.url;
  const hasRelations = relations.length > 0;
  const isHighQuality = source.trust_level && source.trust_level >= 0.75;

  return (
    <Stack spacing={3}>
      {/* Source Metadata */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <Stack spacing={1} sx={{ flex: 1 }}>
            <Typography variant="h4">{source.title ?? t("sources.untitled", "Untitled source")}</Typography>

            <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
              <Chip label={source.kind} size="small" />
              {source.year && <Chip label={source.year} size="small" variant="outlined" />}
              {source.trust_level !== undefined && (
                <Chip
                  label={`Quality: ${Math.round(source.trust_level * 100)}%`}
                  size="small"
                  color={source.trust_level >= 0.9 ? "success" : source.trust_level >= 0.75 ? "info" : "default"}
                />
              )}
            </Box>

            {source.authors && source.authors.length > 0 && (
              <Typography variant="body2" color="text.secondary">
                {source.authors.join(", ")}
              </Typography>
            )}

            {source.origin && (
              <Typography variant="body2" color="text.secondary">
                {source.origin}
              </Typography>
            )}

            {source.url && (
              <Link href={source.url} target="_blank" rel="noopener noreferrer" sx={{ fontSize: "0.875rem" }}>
                {source.url}
              </Link>
            )}

            {source.source_metadata?.pmid && (
              <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
                <Chip label={`PMID: ${source.source_metadata.pmid}`} size="small" icon={<LinkIcon />} />
                {source.source_metadata?.doi && (
                  <Chip label={`DOI: ${source.source_metadata.doi}`} size="small" icon={<LinkIcon />} />
                )}
              </Box>
            )}
          </Stack>

          <Box sx={{ display: "flex", gap: 1 }}>
            <IconButton
              component={RouterLink}
              to={`/sources/${source.id}/edit`}
              color="primary"
              title={t("common.edit", "Edit")}
            >
              <EditIcon />
            </IconButton>
            <IconButton onClick={() => setDeleteDialogOpen(true)} color="error" title={t("common.delete", "Delete")}>
              <DeleteIcon />
            </IconButton>
          </Box>
        </Box>
      </Paper>

      {/* Knowledge Extraction Section - IMPROVED */}
      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <SmartToyIcon color="primary" />
            <Typography variant="h5">{t("sources.extract_knowledge", "Knowledge Extraction")}</Typography>
          </Box>

          {!hasRelations && (
            <Alert severity="info" icon={<AutoFixHighIcon />}>
              {hasUrl ? (
                <>
                  <strong>{t("sources.ready_to_extract", "Ready to extract knowledge!")}</strong>
                  {" "}
                  {t(
                    "sources.auto_extract_hint",
                    "Click the button below to automatically extract entities and relations from this source using AI."
                  )}
                </>
              ) : (
                <>
                  <strong>{t("sources.no_url", "No URL available")}</strong>
                  {" "}
                  {t("sources.upload_hint", "Please upload a PDF or TXT document to extract knowledge.")}
                </>
              )}
            </Alert>
          )}

          {hasRelations && (
            <Alert severity="success">
              {t("sources.has_relations", "This source has {{count}} relations in the knowledge graph.", {
                count: relations.length,
              })}
              {" "}
              {t("sources.can_reextract", "You can extract again to add more knowledge.")}
            </Alert>
          )}

          {uploadError && (
            <Alert severity="error" onClose={() => setUploadError(null)}>
              {uploadError}
            </Alert>
          )}

          {saveResult && (
            <Alert severity="success" onClose={() => setSaveResult(null)}>
              <strong>{t("sources.save_success", "✓ Successfully saved to knowledge graph!")}</strong>
              <br />
              {saveResult.entities_created > 0 && (
                <>
                  {t("sources.entities_created", "{{count}} entities created", {
                    count: saveResult.entities_created,
                  })}
                  <br />
                </>
              )}
              {saveResult.entities_linked > 0 && (
                <>
                  {t("sources.entities_linked", "{{count}} entities linked", {
                    count: saveResult.entities_linked,
                  })}
                  <br />
                </>
              )}
              {saveResult.relations_created > 0 && (
                <>
                  {t("sources.relations_created", "{{count}} relations created", {
                    count: saveResult.relations_created,
                  })}
                </>
              )}
            </Alert>
          )}

          {/* Primary Action: Auto-Extract (Smart) */}
          {hasUrl && (
            <Box>
              <Button
                variant="contained"
                size="large"
                fullWidth
                startIcon={autoExtracting ? <CircularProgress size={20} /> : <AutoFixHighIcon />}
                onClick={handleAutoExtract}
                disabled={autoExtracting || uploading || urlExtracting}
                sx={{
                  py: 2,
                  fontSize: "1.1rem",
                  fontWeight: 600,
                  bgcolor: "primary.main",
                  "&:hover": {
                    bgcolor: "primary.dark",
                  },
                }}
              >
                {autoExtracting
                  ? t("sources.auto_extracting", "Extracting knowledge...")
                  : t("sources.auto_extract", "🤖 Auto-Extract Knowledge from URL")}
              </Button>

              {isHighQuality && (
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", textAlign: "center", mt: 1 }}>
                  {t(
                    "sources.high_quality_hint",
                    "✓ High-quality source detected - extraction will use strict validation"
                  )}
                </Typography>
              )}
            </Box>
          )}

          {/* Secondary Actions: Manual Options */}
          <Divider sx={{ my: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {t("sources.or_manual", "Or choose manual option")}
            </Typography>
          </Divider>

          <Box sx={{ display: "flex", gap: 2 }}>
            <input
              accept=".pdf,.txt"
              style={{ display: "none" }}
              id="document-upload"
              type="file"
              onChange={handleFileUpload}
              disabled={uploading || autoExtracting}
            />
            <label htmlFor="document-upload" style={{ flex: 1 }}>
              <Button
                variant="outlined"
                component="span"
                fullWidth
                startIcon={uploading ? <CircularProgress size={16} /> : <UploadFileIcon />}
                disabled={uploading || autoExtracting}
              >
                {uploading ? t("sources.uploading", "Uploading...") : t("sources.upload_document", "Upload PDF/TXT")}
              </Button>
            </label>

            <Button
              variant="outlined"
              onClick={() => setUrlDialogOpen(true)}
              disabled={uploading || urlExtracting || autoExtracting}
              startIcon={<LinkIcon />}
              sx={{ flex: 1 }}
            >
              {t("sources.extract_from_url", "Custom URL")}
            </Button>
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ display: "block", textAlign: "center" }}>
            {t(
              "sources.extraction_info",
              "AI will analyze the document and suggest entities and relations for your review before adding them to the graph."
            )}
          </Typography>
        </Stack>
      </Paper>

      {/* Extraction Preview - IMPROVED */}
      {extractionPreview && (
        <ExtractionPreview
          preview={extractionPreview}
          onSaveComplete={handleSaveComplete}
          onCancel={handleCancelExtraction}
        />
      )}

      {/* Relations List */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h5">{t("sources.relations", "Relations")}</Typography>
          {hasRelations && (
            <Chip label={`${relations.length} ${t("sources.relations_count", "relations")}`} color="primary" size="small" />
          )}
        </Box>

        <Divider sx={{ mb: 2 }} />

        {relations.length === 0 ? (
          <Alert severity="info">
            {t("sources.no_relations", "No relations yet. Extract knowledge from this source to create relations.")}
          </Alert>
        ) : (
          <List>
            {relations.map((r) => (
              <ListItem
                key={r.id}
                sx={{
                  borderLeft: 3,
                  borderColor: r.direction === "supports" ? "success.main" : r.direction === "contradicts" ? "error.main" : "grey.400",
                  mb: 1,
                  bgcolor: "background.default",
                }}
                secondaryAction={
                  <Box sx={{ display: "flex", gap: 0.5 }}>
                    <IconButton
                      component={RouterLink}
                      to={`/relations/${r.id}/edit`}
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
                      onClick={() => openDeleteRelationDialog(r)}
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
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>
                        {r.kind}
                      </Typography>
                      <Chip
                        label={r.direction}
                        size="small"
                        color={r.direction === "supports" ? "success" : r.direction === "contradicts" ? "error" : "default"}
                        sx={{ fontSize: "0.7rem" }}
                      />
                    </Box>
                  }
                  secondary={
                    <>
                      {r.roles.map((role, idx) => (
                        <Link key={idx} component={RouterLink} to={`/entities/${role.entity_id}`} sx={{ mr: 1 }}>
                          {role.role_type}
                        </Link>
                      ))}
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      {/* Delete Source Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => !deleting && setDeleteDialogOpen(false)}>
        <DialogTitle>{t("source.delete_confirm_title", "Delete Source")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t(
              "source.delete_confirm_message",
              "Are you sure you want to delete this source? This will also delete all relations associated with it. This action cannot be undone."
            )}
          </DialogContentText>
          <Typography variant="body2" sx={{ mt: 2, fontWeight: 600 }}>
            {source.title ?? t("sources.untitled", "Untitled source")}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button onClick={handleDelete} color="error" disabled={deleting}>
            {deleting ? t("common.deleting", "Deleting...") : t("common.delete", "Delete")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Relation Confirmation Dialog */}
      <Dialog open={deleteRelationDialogOpen} onClose={() => !deletingRelation && setDeleteRelationDialogOpen(false)}>
        <DialogTitle>{t("relation.delete_confirm_title", "Delete Relation")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t("relation.delete_confirm_message", "Are you sure you want to delete this relation? This action cannot be undone.")}
          </DialogContentText>
          {relationToDelete && (
            <Typography variant="body2" sx={{ mt: 2, fontWeight: 600 }}>
              {relationToDelete.kind} ({relationToDelete.direction})
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteRelationDialogOpen(false)} disabled={deletingRelation}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button onClick={handleDeleteRelation} color="error" disabled={deletingRelation}>
            {deletingRelation ? t("common.deleting", "Deleting...") : t("common.delete", "Delete")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* URL Extraction Dialog */}
      <UrlExtractionDialog
        open={urlDialogOpen}
        onClose={() => setUrlDialogOpen(false)}
        onSubmit={handleUrlExtraction}
        loading={urlExtracting}
        defaultUrl={source.url}
      />
    </Stack>
  );
}

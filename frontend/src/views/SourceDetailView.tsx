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
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import UploadFileIcon from "@mui/icons-material/UploadFile";

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
      <Typography color="error">
        {t("common.not_found", "Not found")}
      </Typography>
    );
  }

  return (
    <Stack spacing={3}>
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <Typography variant="h4">
              {source.title ?? t("sources.untitled", "Untitled source")}
            </Typography>

            <Typography variant="subtitle2" color="text.secondary">
              {source.kind}
              {source.year && ` • ${source.year}`}
            </Typography>

            {source.url && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                <Link href={source.url} target="_blank" rel="noopener noreferrer">
                  {source.url}
                </Link>
              </Typography>
            )}

            {source.trust_level !== undefined && (
              <Typography variant="body2">
                {t("sources.trust", "Trust level")}:{" "}
                {Math.round(source.trust_level * 100)}%
              </Typography>
            )}
          </div>

          <Box sx={{ display: "flex", gap: 1 }}>
            <IconButton
              component={RouterLink}
              to={`/sources/${source.id}/edit`}
              color="primary"
              title={t("common.edit", "Edit")}
            >
              <EditIcon />
            </IconButton>
            <IconButton
              onClick={() => setDeleteDialogOpen(true)}
              color="error"
              title={t("common.delete", "Delete")}
            >
              <DeleteIcon />
            </IconButton>
          </Box>
        </Box>
      </Paper>

      {/* Document Upload & Extraction */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Knowledge Extraction
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Upload a PDF or TXT document to extract entities and relations using AI.
        </Typography>

        <Box sx={{ display: "flex", gap: 2 }}>
          <input
            accept=".pdf,.txt"
            style={{ display: "none" }}
            id="document-upload"
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
          />
          <label htmlFor="document-upload">
            <Button
              variant="contained"
              component="span"
              startIcon={uploading ? <CircularProgress size={16} /> : <UploadFileIcon />}
              disabled={uploading}
            >
              {uploading ? "Uploading & Extracting..." : "Upload Document"}
            </Button>
          </label>

          <Button
            variant="outlined"
            onClick={() => setUrlDialogOpen(true)}
            disabled={uploading || urlExtracting}
          >
            Extract from URL
          </Button>
        </Box>

        {uploadError && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setUploadError(null)}>
            {uploadError}
          </Alert>
        )}

        {saveResult && (
          <Alert severity="success" sx={{ mt: 2 }} onClose={() => setSaveResult(null)}>
            Successfully saved to graph: {saveResult.entities_created} entities created,{" "}
            {saveResult.entities_linked} entities linked, {saveResult.relations_created}{" "}
            relations created.
          </Alert>
        )}
      </Paper>

      {/* Extraction Preview */}
      {extractionPreview && (
        <ExtractionPreview
          preview={extractionPreview}
          onSaveComplete={handleSaveComplete}
          onCancel={handleCancelExtraction}
        />
      )}

      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          {t("sources.relations", "Relations")}
        </Typography>

        <Divider />

        <List>
          {relations.map((r) => (
            <ListItem
              key={r.id}
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
                primary={`${r.kind} (${r.direction})`}
                secondary={
                  <Link
                    component={RouterLink}
                    to={`/entities/${r.roles[0]?.entity_id}`}
                  >
                    {t("sources.view_entity", "View entity")}
                  </Link>
                }
              />
            </ListItem>
          ))}
        </List>

        {relations.length === 0 && (
          <Typography color="text.secondary">
            {t("sources.no_relations", "No relations")}
          </Typography>
        )}
      </Paper>

      {/* Delete Source Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !deleting && setDeleteDialogOpen(false)}
      >
        <DialogTitle>
          {t("source.delete_confirm_title", "Delete Source")}
        </DialogTitle>
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
            {deleting
              ? t("common.deleting", "Deleting...")
              : t("common.delete", "Delete")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Relation Confirmation Dialog */}
      <Dialog
        open={deleteRelationDialogOpen}
        onClose={() => !deletingRelation && setDeleteRelationDialogOpen(false)}
      >
        <DialogTitle>
          {t("relation.delete_confirm_title", "Delete Relation")}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t(
              "relation.delete_confirm_message",
              "Are you sure you want to delete this relation? This action cannot be undone."
            )}
          </DialogContentText>
          {relationToDelete && (
            <Typography variant="body2" sx={{ mt: 2, fontWeight: 600 }}>
              {relationToDelete.kind} ({relationToDelete.direction})
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDeleteRelationDialogOpen(false)}
            disabled={deletingRelation}
          >
            {t("common.cancel", "Cancel")}
          </Button>
          <Button
            onClick={handleDeleteRelation}
            color="error"
            disabled={deletingRelation}
          >
            {deletingRelation
              ? t("common.deleting", "Deleting...")
              : t("common.delete", "Delete")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* URL Extraction Dialog */}
      <UrlExtractionDialog
        open={urlDialogOpen}
        onClose={() => setUrlDialogOpen(false)}
        onSubmit={handleUrlExtraction}
        loading={urlExtracting}
      />
    </Stack>
  );
}
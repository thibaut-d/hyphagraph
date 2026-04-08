import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useNotification } from "../notifications/NotificationContext";

import {
  Alert,
  Box,
  CircularProgress,
  Stack,
} from "@mui/material";

import { getSource, deleteSource } from "../api/sources";
import { deleteRelation } from "../api/relations";
import { uploadAndExtract, extractFromUrl } from "../api/extraction";
import { SourceRead } from "../types/source";
import { RelationRead } from "../types/relation";
import { invalidateSourceFilterCache } from "../utils/cacheUtils";
import { DocumentExtractionPreview, SaveExtractionResult } from "../types/extraction";
import { ExtractionPreview } from "../components/ExtractionPreview";
import { SourceDetailDialogs } from "../components/source-detail/SourceDetailDialogs";
import { SourceEvidenceSection } from "../components/source-detail/SourceEvidenceSection";
import { SourceExtractionSection } from "../components/source-detail/SourceExtractionSection";
import { SourceMetadataSection } from "../components/source-detail/SourceMetadataSection";
import { SourceRelationsSection } from "../components/source-detail/SourceRelationsSection";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";
import { useSourceRelations } from "../hooks/useSourceRelations";

export function SourceDetailView() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const { t } = useTranslation();
  const { showError } = useNotification();
  const navigate = useNavigate();
  const handlePageError = usePageErrorHandler();

  const {
    relations,
    relationsError,
    reloadRelations,
  } = useSourceRelations(id);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [relationToDelete, setRelationToDelete] = useState<RelationRead | null>(null);
  const [deleteRelationDialogOpen, setDeleteRelationDialogOpen] = useState(false);
  const [deletingRelation, setDeletingRelation] = useState(false);

  // Extraction workflow state
  const [autoExtracting, setAutoExtracting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [extractionPreview, setExtractionPreview] = useState<DocumentExtractionPreview | null>(null);
  const [saveResult, setSaveResult] = useState<SaveExtractionResult | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const lastScrolledRelationIdRef = useRef<string | null>(null);
  const extractionPreviewRef = useRef<HTMLDivElement | null>(null);

  // URL extraction state
  const [urlDialogOpen, setUrlDialogOpen] = useState(false);
  const [urlExtracting, setUrlExtracting] = useState(false);

  const loadSource = useCallback(async (): Promise<SourceRead> => {
    if (!id) {
      throw new Error("Missing source ID");
    }

    const sourceData = await getSource(id);
    await reloadRelations();
    return sourceData;
  }, [id, reloadRelations]);

  const {
    data: source,
    loading,
    error,
  } = useAsyncResource<SourceRead>({
    enabled: Boolean(id),
    deps: [id],
    load: loadSource,
    onError: (err) => handlePageError(err, "Failed to load source").userMessage,
  });

  const highlightedRelationId = searchParams.get("relation");

  useEffect(() => {
    if (!highlightedRelationId || relations.length === 0) {
      return;
    }

    if (lastScrolledRelationIdRef.current === highlightedRelationId) {
      return;
    }

    const relationExists = relations.some((relation) => relation.id === highlightedRelationId);
    if (!relationExists) {
      return;
    }

    const row = document.getElementById(`relation-${highlightedRelationId}`);
    if (!row) {
      return;
    }

    row.scrollIntoView({ behavior: "smooth", block: "center" });
    lastScrolledRelationIdRef.current = highlightedRelationId;
  }, [highlightedRelationId, relations]);

  useEffect(() => {
    if (!extractionPreview) {
      return;
    }

    extractionPreviewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [extractionPreview]);

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
      showError(error);
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteRelation = async () => {
    if (!relationToDelete || !id) return;

    setDeletingRelation(true);
    try {
      await deleteRelation(relationToDelete.id);
      await reloadRelations();
      setDeleteRelationDialogOpen(false);
      setRelationToDelete(null);
    } catch (error) {
      showError(error);
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
    setSaveResult(null);

    try {
      // Smart detection: use source URL for extraction
      if (source.url) {
        const preview = await extractFromUrl(id, source.url);
        setExtractionPreview(preview);
      } else {
        // No source URL is available, so route the user into the URL flow directly.
        setUrlDialogOpen(true);
      }
    } catch (error) {
      showError(error);
    } finally {
      setAutoExtracting(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !id) return;

    setUploading(true);
    setSaveResult(null);
    setUploadedFileName(file.name);

    try {
      const preview = await uploadAndExtract(id, file);
      setExtractionPreview(preview);
    } catch (error) {
      showError(error);
      setUploadedFileName(null);
    } finally {
      setUploading(false);
      // Clear file input
      event.target.value = "";
    }
  };

  const handleSaveComplete = async (result: SaveExtractionResult) => {
    setSaveResult(result);
    setExtractionPreview(null);

    await reloadRelations();
  };

  const handleCancelExtraction = () => {
    setExtractionPreview(null);
    setUploadedFileName(null);
  };

  const handleUrlExtraction = async (url: string) => {
    if (!id) return;

    setUrlExtracting(true);
    setSaveResult(null);

    try {
      const preview = await extractFromUrl(id, url);
      setExtractionPreview(preview);
      setUrlDialogOpen(false);
    } catch (error) {
      showError(error);
      throw error; // Re-throw to let dialog handle error display
    } finally {
      setUrlExtracting(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !source) {
    return <Alert severity="error">{error || t("common.error", "An error occurred")}</Alert>;
  }

  const hasUrl = !!source.url;
  const hasRelations = relations.length > 0;
  const isHighQuality = source.trust_level != null && source.trust_level >= 0.75;
  const statementCount = relations.filter((relation) => {
    if (!relation.notes) {
      return false;
    }

    if (typeof relation.notes === "string") {
      return relation.notes.trim().length > 0;
    }

    return Object.values(relation.notes).some((value) => value.trim().length > 0);
  }).length;

  return (
    <Stack spacing={3}>
      <SourceMetadataSection
        source={source}
        relationsCount={relations.length}
        statementsCount={statementCount}
        onDelete={() => setDeleteDialogOpen(true)}
      />

      <SourceEvidenceSection
        source={source}
        relations={relations}
      />

      {extractionPreview && (
        <Box ref={extractionPreviewRef}>
          <ExtractionPreview
            preview={extractionPreview}
            onSaveComplete={handleSaveComplete}
            onCancel={handleCancelExtraction}
          />
        </Box>
      )}

      <SourceRelationsSection
        relations={relations}
        relationsError={relationsError}
        highlightedRelationId={highlightedRelationId}
        onDeleteRelation={openDeleteRelationDialog}
      />

      <SourceExtractionSection
        hasUrl={hasUrl}
        hasRelations={hasRelations}
        relationsCount={relations.length}
        relationsError={relationsError}
        isHighQuality={isHighQuality}
        autoExtracting={autoExtracting}
        uploading={uploading}
        urlExtracting={urlExtracting}
        uploadedFileName={uploadedFileName}
        saveResult={saveResult}
        onClearSaveResult={() => setSaveResult(null)}
        onAutoExtract={() => void handleAutoExtract()}
        onFileUpload={handleFileUpload}
        onOpenUrlDialog={() => setUrlDialogOpen(true)}
        onClearUploadedFile={() => setUploadedFileName(null)}
      />

      <SourceDetailDialogs
        source={source}
        deleteDialogOpen={deleteDialogOpen}
        deleting={deleting}
        onCloseDeleteDialog={() => setDeleteDialogOpen(false)}
        onConfirmDelete={() => void handleDelete()}
        deleteRelationDialogOpen={deleteRelationDialogOpen}
        deletingRelation={deletingRelation}
        relationToDelete={relationToDelete}
        onCloseDeleteRelationDialog={() => setDeleteRelationDialogOpen(false)}
        onConfirmDeleteRelation={() => void handleDeleteRelation()}
        urlDialogOpen={urlDialogOpen}
        urlExtracting={urlExtracting}
        onCloseUrlDialog={() => setUrlDialogOpen(false)}
        onSubmitUrlExtraction={handleUrlExtraction}
      />
    </Stack>
  );
}

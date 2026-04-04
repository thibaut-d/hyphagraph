import { useTranslation } from "react-i18next";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Typography,
} from "@mui/material";

import { UrlExtractionDialog } from "../UrlExtractionDialog";
import type { RelationRead } from "../../types/relation";
import type { SourceRead } from "../../types/source";

interface SourceDetailDialogsProps {
  source: SourceRead;
  deleteDialogOpen: boolean;
  deleting: boolean;
  onCloseDeleteDialog: () => void;
  onConfirmDelete: () => void;
  deleteRelationDialogOpen: boolean;
  deletingRelation: boolean;
  relationToDelete: RelationRead | null;
  onCloseDeleteRelationDialog: () => void;
  onConfirmDeleteRelation: () => void;
  urlDialogOpen: boolean;
  urlExtracting: boolean;
  onCloseUrlDialog: () => void;
  onSubmitUrlExtraction: (url: string) => Promise<void>;
}

export function SourceDetailDialogs({
  source,
  deleteDialogOpen,
  deleting,
  onCloseDeleteDialog,
  onConfirmDelete,
  deleteRelationDialogOpen,
  deletingRelation,
  relationToDelete,
  onCloseDeleteRelationDialog,
  onConfirmDeleteRelation,
  urlDialogOpen,
  urlExtracting,
  onCloseUrlDialog,
  onSubmitUrlExtraction,
}: SourceDetailDialogsProps) {
  const { t } = useTranslation();

  return (
    <>
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !deleting && onCloseDeleteDialog()}
        transitionDuration={0}
      >
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
          <Button onClick={onCloseDeleteDialog} disabled={deleting}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button onClick={onConfirmDelete} color="error" disabled={deleting}>
            {deleting ? t("common.deleting", "Deleting...") : t("common.delete", "Delete")}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteRelationDialogOpen}
        onClose={() => !deletingRelation && onCloseDeleteRelationDialog()}
        transitionDuration={0}
      >
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
          <Button onClick={onCloseDeleteRelationDialog} disabled={deletingRelation}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button onClick={onConfirmDeleteRelation} color="error" disabled={deletingRelation}>
            {deletingRelation ? t("common.deleting", "Deleting...") : t("common.delete", "Delete")}
          </Button>
        </DialogActions>
      </Dialog>

      <UrlExtractionDialog
        open={urlDialogOpen}
        onClose={onCloseUrlDialog}
        onSubmit={onSubmitUrlExtraction}
        loading={urlExtracting}
        defaultUrl={source.url || undefined}
      />
    </>
  );
}

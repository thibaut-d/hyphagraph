import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Typography,
} from "@mui/material";
import { EntityRead } from "../../types/entity";

/**
 * Delete confirmation dialog for entities.
 *
 * Displays entity slug and confirmation message with cancel/delete actions.
 * Disables actions and shows "Deleting..." state while deletion is in progress.
 */
export interface EntityDeleteDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** The entity to be deleted */
  entity: EntityRead;
  /** Whether the deletion operation is in progress */
  deleting: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** Callback to confirm deletion */
  onConfirm: () => void;
}

export function EntityDeleteDialog({
  open,
  entity,
  deleting,
  onClose,
  onConfirm,
}: EntityDeleteDialogProps) {
  const { t } = useTranslation();

  return (
    <Dialog open={open} onClose={() => !deleting && onClose()}>
      <DialogTitle>
        {t("entity.delete_confirm_title", "Delete Entity")}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          {t(
            "entity.delete_confirm_message",
            "Are you sure you want to delete this entity? This action cannot be undone."
          )}
        </DialogContentText>
        <Typography variant="body2" sx={{ mt: 2, fontWeight: 600 }}>
          {entity.slug}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={deleting}>
          {t("common.cancel", "Cancel")}
        </Button>
        <Button onClick={onConfirm} color="error" disabled={deleting}>
          {deleting
            ? t("common.deleting", "Deleting...")
            : t("common.delete", "Delete")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

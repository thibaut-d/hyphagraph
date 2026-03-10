import { useState } from "react";
import { deleteEntity } from "../api/entities";
import { useNotification } from "../notifications/NotificationContext";

/**
 * Hook for managing entity deletion dialog and operation.
 *
 * Provides state for delete confirmation dialog and handles the deletion operation.
 * Shows success/error notifications and calls onSuccess callback after deletion.
 *
 * @returns Dialog state, deleting state, and dialog/deletion handlers
 */
export interface UseEntityDeletionReturn {
  isDialogOpen: boolean;
  isDeleting: boolean;
  openDialog: () => void;
  closeDialog: () => void;
  confirmDelete: (entityId: string, onSuccess: () => void) => Promise<void>;
}

export function useEntityDeletion(): UseEntityDeletionReturn {
  const { showError, showSuccess } = useNotification();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const openDialog = () => setIsDialogOpen(true);
  const closeDialog = () => setIsDialogOpen(false);

  const confirmDelete = async (entityId: string, onSuccess: () => void) => {
    setIsDeleting(true);
    try {
      await deleteEntity(entityId);
      showSuccess("Entity deleted successfully");
      closeDialog();
      onSuccess();
    } catch (error) {
      showError(error);
    } finally {
      setIsDeleting(false);
    }
  };

  return {
    isDialogOpen,
    isDeleting,
    openDialog,
    closeDialog,
    confirmDelete,
  };
}

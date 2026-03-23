import { useState, useCallback } from "react";
import {
  reviewExtraction,
  batchReview,
  type ReviewDecision,
} from "../api/extractionReview";
import { useNotification } from "../notifications/NotificationContext";
import { usePageErrorHandler } from "./usePageErrorHandler";

/**
 * Hook for managing review dialog state and submission.
 *
 * Handles review dialog open/close state, form inputs (notes, decision),
 * and review submission (single or batch).
 *
 * @returns Review dialog state and actions
 */
export interface UseReviewDialogReturn {
  isOpen: boolean;
  notes: string;
  decision: "approve" | "reject";
  setNotes: (notes: string) => void;
  setDecision: (decision: "approve" | "reject") => void;
  openDialog: (decision: "approve" | "reject") => void;
  closeDialog: () => void;
  submitReview: (extractionId: string, onSuccess?: () => void, decisionOverride?: "approve" | "reject") => Promise<void>;
  submitBatchReview: (extractionIds: Set<string>, onSuccess?: () => void) => Promise<void>;
  isSubmitting: boolean;
}

export function useReviewDialog(): UseReviewDialogReturn {
  const { showError, showSuccess } = useNotification();
  const handlePageError = usePageErrorHandler();
  const [isOpen, setIsOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [decision, setDecision] = useState<"approve" | "reject">("approve");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const openDialog = useCallback((defaultDecision: "approve" | "reject" = "approve") => {
    setDecision(defaultDecision);
    setNotes("");
    setIsOpen(true);
  }, []);

  const closeDialog = useCallback(() => {
    setIsOpen(false);
    setNotes("");
  }, []);

  const submitReview = useCallback(
    async (extractionId: string, onSuccess?: () => void, decisionOverride?: "approve" | "reject") => {
      const effectiveDecision = decisionOverride ?? decision;
      setIsSubmitting(true);
      try {
        await reviewExtraction(extractionId, {
          decision: effectiveDecision as ReviewDecision,
          notes: notes || undefined,
        });

        const message =
          effectiveDecision === "approve"
            ? "Extraction approved"
            : "Extraction rejected";
        showSuccess(message);

        closeDialog();
        if (onSuccess) {
          onSuccess();
        }
      } catch (err) {
        handlePageError(err, "Failed to submit review");
      } finally {
        setIsSubmitting(false);
      }
    },
    [closeDialog, decision, handlePageError, notes, showSuccess]
  );

  const submitBatchReview = useCallback(
    async (extractionIds: Set<string>, onSuccess?: () => void) => {
      if (extractionIds.size === 0) {
        showError("No extractions selected");
        return;
      }

      setIsSubmitting(true);
      try {
        const response = await batchReview({
          extraction_ids: Array.from(extractionIds),
          decision: decision as ReviewDecision,
          notes: notes || undefined,
        });

        if (response.failed > 0 && response.succeeded === 0) {
          showError(
            `Batch review failed: all ${response.failed} extractions could not be processed`
          );
          return;
        }

        if (response.failed > 0) {
          const verb = decision === "approve" ? "approved" : "rejected";
          showError(
            `Partial success: ${response.succeeded} extractions ${verb}, ${response.failed} failed`
          );
        } else {
          const message =
            decision === "approve"
              ? `${response.succeeded} extractions approved`
              : `${response.succeeded} extractions rejected`;
          showSuccess(message);
        }

        closeDialog();
        if (onSuccess) {
          onSuccess();
        }
      } catch (err) {
        handlePageError(err, "Failed to submit batch review");
      } finally {
        setIsSubmitting(false);
      }
    },
    [closeDialog, decision, handlePageError, notes, showError, showSuccess]
  );

  return {
    isOpen,
    notes,
    decision,
    setNotes,
    setDecision,
    openDialog,
    closeDialog,
    submitReview,
    submitBatchReview,
    isSubmitting,
  };
}

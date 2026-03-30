import { useCallback, useState } from "react";

import { parseError } from "../utils/errorHandler";
import { useNotification } from "../notifications/NotificationContext";

type ActionResult<T> =
  | { ok: true; value: T }
  | { ok: false };

/**
 * Hook for user-triggered async mutations (form submissions, deletions, etc.).
 *
 * Error display rule:
 * - With `setError`: error message written to local state for inline display;
 *   the Snackbar toast is suppressed (inline display only).
 * - Without `setError`: error shown as a Snackbar toast (no inline state).
 *
 * Use `useAsyncResource` for data-fetch lifecycle (loading + data + error state).
 * Use `usePageErrorHandler` only for one-off error display outside of an action.
 */
export function useAsyncAction(
  setError?: (message: string | null) => void
) {
  const { showError } = useNotification();
  const [isRunning, setIsRunning] = useState(false);

  const run = useCallback(
    async <T>(
      action: () => Promise<T>,
      fallbackMessage: string
    ): Promise<ActionResult<T>> => {
      setIsRunning(true);
      setError?.(null);

      try {
        const value = await action();
        return { ok: true, value };
      } catch (error) {
        if (setError) {
          // Inline display: write the user message to local state; no toast.
          const parsedError = parseError(error, fallbackMessage);
          setError(parsedError.userMessage);
        } else {
          // Toast display: delegate to the notification system.
          showError(error);
        }
        return { ok: false };
      } finally {
        setIsRunning(false);
      }
    },
    [showError, setError]
  );

  return {
    isRunning,
    run,
  };
}

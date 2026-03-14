import { useCallback, useState } from "react";

import { usePageErrorHandler } from "./usePageErrorHandler";

type ActionResult<T> =
  | { ok: true; value: T }
  | { ok: false };

export function useAsyncAction(
  setError?: (message: string | null) => void
) {
  const handlePageError = usePageErrorHandler();
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
        const parsedError = handlePageError(error, fallbackMessage);
        setError?.(parsedError.userMessage);
        return { ok: false };
      } finally {
        setIsRunning(false);
      }
    },
    [handlePageError, setError]
  );

  return {
    isRunning,
    run,
  };
}

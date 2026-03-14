import { useCallback } from "react";

import { useNotification } from "../notifications/NotificationContext";
import { parseError, type ParsedError } from "../utils/errorHandler";

export function usePageErrorHandler() {
  const { showError } = useNotification();

  return useCallback(
    (error: unknown, fallbackMessage: string): ParsedError => {
      const parsedError = parseError(error, fallbackMessage);
      showError(error);
      return parsedError;
    },
    [showError]
  );
}

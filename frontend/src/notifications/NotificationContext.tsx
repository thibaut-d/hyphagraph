import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from "react";
import { Snackbar, Alert, IconButton, Slide } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";
import { parseError, ParsedError } from "../utils/errorHandler";

type NotificationSeverity = "success" | "error" | "info" | "warning";

interface Notification {
  id: string;
  message: string;
  severity: NotificationSeverity;
  autoDismiss: boolean;
  duration: number;
  parsedError?: ParsedError; // Store parsed error for detailed display
}

interface NotificationOptions {
  autoDismiss?: boolean;
  duration?: number;
}

interface NotificationContextValue {
  showSuccess: (message: string, options?: NotificationOptions) => void;
  showError: (messageOrError: string | Error | any, options?: NotificationOptions) => void;
  showInfo: (message: string, options?: NotificationOptions) => void;
  showWarning: (message: string, options?: NotificationOptions) => void;
  dismiss: () => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(
  null,
);

const DEFAULT_DURATIONS: Record<NotificationSeverity, number> = {
  success: 4000,
  info: 5000,
  warning: 7000,
  error: 10000,
};

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [queue, setQueue] = useState<Notification[]>([]);
  const [current, setCurrent] = useState<Notification | null>(null);

  // Process queue when current notification is cleared
  useEffect(() => {
    if (!current && queue.length > 0) {
      const [next, ...rest] = queue;
      setCurrent(next);
      setQueue(rest);
    }
  }, [current, queue]);

  // Auto-dismiss current notification after timeout
  useEffect(() => {
    if (current && current.autoDismiss) {
      const timer = setTimeout(() => {
        setCurrent(null);
      }, current.duration);

      return () => clearTimeout(timer);
    }
  }, [current]);

  const addNotification = useCallback(
    (
      message: string,
      severity: NotificationSeverity,
      options?: NotificationOptions,
    ) => {
      const notification: Notification = {
        id: `${Date.now()}-${Math.random()}`,
        message,
        severity,
        autoDismiss: options?.autoDismiss ?? true,
        duration: options?.duration ?? DEFAULT_DURATIONS[severity],
      };

      setQueue((prev) => [...prev, notification]);
    },
    [],
  );

  const showSuccess = useCallback(
    (message: string, options?: NotificationOptions) => {
      addNotification(message, "success", options);
    },
    [addNotification],
  );

  const showError = useCallback(
    (messageOrError: string | Error | any, options?: NotificationOptions) => {
      // If it's not a string, parse it as an error
      if (typeof messageOrError !== "string") {
        const parsedError = parseError(messageOrError);

        // Log the full error to console for debugging
        console.error("Error notification:", {
          userMessage: parsedError.userMessage,
          developerMessage: parsedError.developerMessage,
          code: parsedError.code,
          field: parsedError.field,
          context: parsedError.context,
        });

        // Show user-friendly message in notification
        const notification: Notification = {
          id: `${Date.now()}-${Math.random()}`,
          message: parsedError.userMessage,
          severity: "error",
          autoDismiss: options?.autoDismiss ?? true,
          duration: options?.duration ?? DEFAULT_DURATIONS.error,
          parsedError, // Store for potential detailed display
        };

        setQueue((prev) => [...prev, notification]);
      } else {
        // String message - use existing logic
        addNotification(messageOrError, "error", options);
      }
    },
    [addNotification],
  );

  const showInfo = useCallback(
    (message: string, options?: NotificationOptions) => {
      addNotification(message, "info", options);
    },
    [addNotification],
  );

  const showWarning = useCallback(
    (message: string, options?: NotificationOptions) => {
      addNotification(message, "warning", options);
    },
    [addNotification],
  );

  const dismiss = useCallback(() => {
    setCurrent(null);
  }, []);

  // Try to translate message, fall back to raw message if not found
  const displayMessage = current
    ? t(current.message, { defaultValue: current.message })
    : "";

  return (
    <NotificationContext.Provider
      value={{ showSuccess, showError, showInfo, showWarning, dismiss }}
    >
      {children}
      <Snackbar
        open={!!current}
        onClose={dismiss}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        TransitionComponent={Slide}
      >
        <Alert
          severity={current?.severity}
          onClose={dismiss}
          action={
            <IconButton
              size="small"
              aria-label="close"
              color="inherit"
              onClick={dismiss}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          }
          sx={{ width: "100%" }}
        >
          {displayMessage}
        </Alert>
      </Snackbar>
    </NotificationContext.Provider>
  );
}

export function useNotification() {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error(
      "useNotification must be used within NotificationProvider",
    );
  }
  return ctx;
}

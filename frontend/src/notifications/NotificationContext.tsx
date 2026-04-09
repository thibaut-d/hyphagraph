import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
  type SyntheticEvent,
} from "react";
import {
  Snackbar,
  Alert,
  IconButton,
  Slide,
  Box,
  Collapse,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";
import { parseError, formatErrorForLogging, ParsedError } from "../utils/errorHandler";

const IS_DEV = import.meta.env.DEV;

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
  showError: (messageOrError: string | Error | unknown, options?: NotificationOptions) => void;
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

const MAX_QUEUE_SIZE = 10;

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [queue, setQueue] = useState<Notification[]>([]);
  const [current, setCurrent] = useState<Notification | null>(null);
  const [devDetailsOpen, setDevDetailsOpen] = useState(false);

  // Reset dev details panel whenever a new notification becomes current
  useEffect(() => {
    setDevDetailsOpen(false);
  }, [current?.id]);

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

      setQueue((prev) => {
        // Implement queue size limit - drop oldest notifications when limit exceeded
        const updatedQueue = [...prev, notification];
        if (updatedQueue.length > MAX_QUEUE_SIZE) {
          return updatedQueue.slice(updatedQueue.length - MAX_QUEUE_SIZE);
        }
        return updatedQueue;
      });
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
    (messageOrError: string | Error | unknown, options?: NotificationOptions) => {
      // If it's not a string, parse it as an error
      if (typeof messageOrError !== "string") {
        const parsedError = parseError(messageOrError);

        // Log full structured error for debugging
        console.error(formatErrorForLogging(parsedError));

        // Show user-friendly message in notification
        const notification: Notification = {
          id: `${Date.now()}-${Math.random()}`,
          message: parsedError.userMessage,
          severity: "error",
          autoDismiss: options?.autoDismiss ?? true,
          duration: options?.duration ?? DEFAULT_DURATIONS.error,
          parsedError,
        };

        setQueue((prev) => {
          const updatedQueue = [...prev, notification];
          if (updatedQueue.length > MAX_QUEUE_SIZE) {
            return updatedQueue.slice(updatedQueue.length - MAX_QUEUE_SIZE);
          }
          return updatedQueue;
        });
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

  const handleClose = useCallback(
    (_event?: Event | SyntheticEvent, reason?: string) => {
      // Keep the notification open while the user interacts with its content,
      // including the dev-details disclosure.
      if (reason === "clickaway") {
        return;
      }
      dismiss();
    },
    [dismiss],
  );

  // Try to translate message, fall back to raw message if not found
  const displayMessage = current
    ? t(current.message, { defaultValue: current.message })
    : "";

  const devError = IS_DEV ? current?.parsedError : undefined;

  return (
    <NotificationContext.Provider
      value={{ showSuccess, showError, showInfo, showWarning, dismiss }}
    >
      {children}
      <Snackbar
        open={!!current}
        onClose={handleClose}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        TransitionComponent={Slide}
      >
        <Alert
          severity={current?.severity}
          onClose={handleClose}
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

          {/* Dev-mode expandable error details — never rendered in production */}
          {devError && (
            <Box sx={{ mt: 0.5 }}>
              <Box
                component="button"
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  setDevDetailsOpen((o) => !o);
                }}
                sx={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "11px",
                  opacity: 0.7,
                  p: 0,
                  color: "inherit",
                  textDecoration: "underline",
                }}
              >
                {devDetailsOpen ? "▾ Dev details" : "▸ Dev details"}
              </Box>
              <Collapse in={devDetailsOpen}>
                <Box
                  sx={{
                    mt: 0.5,
                    p: 1,
                    background: "rgba(0,0,0,0.08)",
                    borderRadius: 1,
                    fontFamily: "monospace",
                    fontSize: "11px",
                    wordBreak: "break-all",
                  }}
                >
                  <Typography variant="inherit" component="div">
                    <strong>code:</strong> {devError.code}
                  </Typography>
                  <Typography variant="inherit" component="div" sx={{ mt: 0.25 }}>
                    <strong>dev:</strong> {devError.developerMessage}
                  </Typography>
                  {devError.field && (
                    <Typography variant="inherit" component="div" sx={{ mt: 0.25 }}>
                      <strong>field:</strong> {devError.field}
                    </Typography>
                  )}
                  {devError.context && (
                    <Typography variant="inherit" component="div" sx={{ mt: 0.25 }}>
                      <strong>ctx:</strong> {JSON.stringify(devError.context)}
                    </Typography>
                  )}
                </Box>
              </Collapse>
            </Box>
          )}
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

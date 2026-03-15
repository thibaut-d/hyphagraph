/**
 * ErrorDetails component for displaying detailed error information.
 *
 * This component is useful for:
 * - Debugging errors during development
 * - Providing users with detailed error context
 * - Copying error details for bug reports
 */
import { useState } from "react";
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  IconButton,
  Alert,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { ParsedError, getErrorTitle, parseError } from "../utils/errorHandler";
import { useNotification } from "../notifications/NotificationContext";

interface ErrorDetailsProps {
  error: ParsedError;
  /** Whether to show in compact mode (less details) */
  compact?: boolean;
  /** Whether to show the copy button */
  showCopy?: boolean;
}

export function ErrorDetails({
  error,
  compact = false,
  showCopy = true,
}: ErrorDetailsProps) {
  const [expanded, setExpanded] = useState(!compact);
  const { showSuccess } = useNotification();

  const handleCopy = () => {
    const errorText = JSON.stringify(
      {
        code: error.code,
        userMessage: error.userMessage,
        developerMessage: error.developerMessage,
        field: error.field,
        context: error.context,
        statusCode: error.statusCode,
      },
      null,
      2,
    );

    navigator.clipboard.writeText(errorText).then(() => {
      showSuccess("Error details copied to clipboard");
    });
  };

  return (
    <Box>
      <Alert severity="error" sx={{ mb: 2 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" fontWeight="bold">
              {getErrorTitle(error.code)}
            </Typography>
            <Typography variant="body2">{error.userMessage}</Typography>
          </Box>
          {showCopy && (
            <IconButton
              size="small"
              onClick={handleCopy}
              title="Copy error details"
            >
              <ContentCopyIcon fontSize="small" />
            </IconButton>
          )}
        </Box>
      </Alert>

      <Accordion expanded={expanded} onChange={() => setExpanded(!expanded)}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle2">Error Details</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {/* Error Code */}
            <Box>
              <Typography variant="caption" color="text.secondary">
                Error Code
              </Typography>
              <Box sx={{ mt: 0.5 }}>
                <Chip label={error.code} size="small" color="error" />
              </Box>
            </Box>

            {/* Status Code */}
            {error.statusCode && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  HTTP Status
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  {error.statusCode}
                </Typography>
              </Box>
            )}

            {/* Field (for validation errors) */}
            {error.field && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Field
                </Typography>
                <Typography
                  variant="body2"
                  sx={{ mt: 0.5, fontFamily: "monospace" }}
                >
                  {error.field}
                </Typography>
              </Box>
            )}

            {/* Developer Message */}
            <Box>
              <Typography variant="caption" color="text.secondary">
                Developer Message
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  mt: 0.5,
                  fontFamily: "monospace",
                  fontSize: "0.85rem",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {error.developerMessage}
              </Typography>
            </Box>

            {/* Context Data */}
            {error.context && Object.keys(error.context).length > 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Context
                </Typography>
                <Box
                  sx={{
                    mt: 0.5,
                    p: 1,
                    bgcolor: "grey.100",
                    borderRadius: 1,
                    fontFamily: "monospace",
                    fontSize: "0.75rem",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    overflow: "auto",
                    maxHeight: "200px",
                  }}
                >
                  {JSON.stringify(error.context, null, 2)}
                </Box>
              </Box>
            )}
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}

/**
 * Hook to easily show error details in a modal or section.
 *
 * Usage:
 *   const { showErrorDetails } = useErrorDetails();
 *   try {
 *     await someApiCall();
 *   } catch (error) {
 *     showErrorDetails(error);
 *   }
 */
export function useErrorDetails() {
  const [currentError, setCurrentError] = useState<ParsedError | null>(null);

  const showErrorDetails = (error: ParsedError | unknown) => {
    const parsed =
      error && typeof error === "object" && "code" in error
        ? (error as ParsedError)
        : parseError(error);
    setCurrentError(parsed);
  };

  const clearError = () => {
    setCurrentError(null);
  };

  return {
    currentError,
    showErrorDetails,
    clearError,
  };
}

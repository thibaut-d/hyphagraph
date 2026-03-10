/**
 * Unified error handling system for HyphaGraph frontend.
 *
 * This module provides:
 * - Error parsing from various sources (API, validation, network)
 * - User-friendly error messages with debugging information
 * - Integration with i18n for localized error messages
 */

/**
 * Error codes from the backend.
 * Keep in sync with backend/app/utils/errors.py::ErrorCode
 */
export enum ErrorCode {
  // Generic errors
  INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR",
  VALIDATION_ERROR = "VALIDATION_ERROR",
  NOT_FOUND = "NOT_FOUND",
  UNAUTHORIZED = "UNAUTHORIZED",
  FORBIDDEN = "FORBIDDEN",
  RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED",

  // Authentication errors
  AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS",
  AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED",
  AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID",
  AUTH_EMAIL_NOT_VERIFIED = "AUTH_EMAIL_NOT_VERIFIED",
  AUTH_ACCOUNT_DEACTIVATED = "AUTH_ACCOUNT_DEACTIVATED",
  AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS",

  // User management errors
  USER_EMAIL_ALREADY_EXISTS = "USER_EMAIL_ALREADY_EXISTS",
  USER_NOT_FOUND = "USER_NOT_FOUND",
  USER_WEAK_PASSWORD = "USER_WEAK_PASSWORD",
  USER_INVALID_EMAIL = "USER_INVALID_EMAIL",

  // Entity/Relation errors
  ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND",
  ENTITY_SLUG_CONFLICT = "ENTITY_SLUG_CONFLICT",
  RELATION_NOT_FOUND = "RELATION_NOT_FOUND",
  RELATION_TYPE_NOT_FOUND = "RELATION_TYPE_NOT_FOUND",
  SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND",

  // LLM/Extraction errors
  LLM_SERVICE_UNAVAILABLE = "LLM_SERVICE_UNAVAILABLE",
  LLM_API_ERROR = "LLM_API_ERROR",
  LLM_RATE_LIMIT = "LLM_RATE_LIMIT",
  EXTRACTION_FAILED = "EXTRACTION_FAILED",
  EXTRACTION_TEXT_TOO_LONG = "EXTRACTION_TEXT_TOO_LONG",
  EXTRACTION_TEXT_TOO_SHORT = "EXTRACTION_TEXT_TOO_SHORT",

  // Document/File errors
  DOCUMENT_PARSE_ERROR = "DOCUMENT_PARSE_ERROR",
  DOCUMENT_TOO_LARGE = "DOCUMENT_TOO_LARGE",
  DOCUMENT_UNSUPPORTED_FORMAT = "DOCUMENT_UNSUPPORTED_FORMAT",
  DOCUMENT_FETCH_FAILED = "DOCUMENT_FETCH_FAILED",

  // Database errors
  DATABASE_ERROR = "DATABASE_ERROR",
  DATABASE_CONSTRAINT_VIOLATION = "DATABASE_CONSTRAINT_VIOLATION",
  DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR",

  // Business logic errors
  INVALID_FILTER_COMBINATION = "INVALID_FILTER_COMBINATION",
  INVALID_DATE_RANGE = "INVALID_DATE_RANGE",
  INVALID_PAGINATION = "INVALID_PAGINATION",
  MERGE_CONFLICT = "MERGE_CONFLICT",
  CIRCULAR_RELATION_DETECTED = "CIRCULAR_RELATION_DETECTED",

  // Frontend-only errors
  NETWORK_ERROR = "NETWORK_ERROR",
  UNKNOWN_ERROR = "UNKNOWN_ERROR",
}

/**
 * Structured error detail from backend.
 */
export interface ErrorDetail {
  code: ErrorCode;
  message: string;
  details?: string;
  field?: string;
  context?: Record<string, any>;
}

/**
 * Parsed error information for display.
 */
export interface ParsedError {
  /** User-friendly message (can be shown in notifications) */
  userMessage: string;

  /** Developer-friendly details (for debugging) */
  developerMessage: string;

  /** Error code for programmatic handling */
  code: ErrorCode;

  /** Field name for validation errors */
  field?: string;

  /** Additional context data */
  context?: Record<string, any>;

  /** Original error for logging */
  originalError?: any;

  /** HTTP status code if applicable */
  statusCode?: number;
}

/**
 * Parse an error from any source into a standardized format.
 *
 * Handles:
 * - Backend API errors with ErrorDetail structure
 * - Network errors (fetch failures)
 * - Validation errors
 * - Generic JavaScript errors
 *
 * @param error - The error to parse (can be Error, Response, or any)
 * @param fallbackMessage - Message to use if error cannot be parsed
 */
export function parseError(
  error: any,
  fallbackMessage: string = "An unexpected error occurred",
): ParsedError {
  // If already a ParsedError, return it
  if (error && typeof error === "object" && "userMessage" in error && "code" in error) {
    return error as ParsedError;
  }

  // Handle Error instances with structured detail
  if (error instanceof Error) {
    // Check if the error message is a JSON string (from apiFetch)
    try {
      const parsed = JSON.parse(error.message);
      if (parsed && typeof parsed === "object") {
        // Backend validation error format
        if (Array.isArray(parsed)) {
          const firstError = parsed[0];
          return {
            userMessage: `Invalid ${firstError.loc?.join(".")}: ${firstError.msg}`,
            developerMessage: JSON.stringify(parsed, null, 2),
            code: ErrorCode.VALIDATION_ERROR,
            field: firstError.loc?.join("."),
            context: { validation_errors: parsed },
            originalError: error,
          };
        }

        // Backend error detail format
        if (parsed.code && parsed.message) {
          return {
            userMessage: parsed.message,
            developerMessage: parsed.details || parsed.message,
            code: parsed.code as ErrorCode,
            field: parsed.field,
            context: parsed.context,
            originalError: error,
          };
        }
      }
    } catch {
      // Not JSON, continue with regular error handling
    }

    // Check for network errors
    if (
      error.message.includes("fetch") ||
      error.message.includes("network") ||
      error.message.toLowerCase().includes("failed to fetch")
    ) {
      return {
        userMessage: "Network error. Please check your connection.",
        developerMessage: `Network request failed: ${error.message}`,
        code: ErrorCode.NETWORK_ERROR,
        originalError: error,
      };
    }

    // Generic Error instance
    return {
      userMessage: error.message || fallbackMessage,
      developerMessage: error.stack || error.message || fallbackMessage,
      code: ErrorCode.UNKNOWN_ERROR,
      originalError: error,
    };
  }

  // Handle Response objects
  if (error && typeof error === "object" && "status" in error && "statusText" in error) {
    const statusCode = error.status as number;
    let code = ErrorCode.UNKNOWN_ERROR;
    let userMessage = fallbackMessage;

    if (statusCode === 401) {
      code = ErrorCode.UNAUTHORIZED;
      userMessage = "Unauthorized. Please log in.";
    } else if (statusCode === 403) {
      code = ErrorCode.FORBIDDEN;
      userMessage = "You don't have permission to perform this action.";
    } else if (statusCode === 404) {
      code = ErrorCode.NOT_FOUND;
      userMessage = "The requested resource was not found.";
    } else if (statusCode === 429) {
      code = ErrorCode.RATE_LIMIT_EXCEEDED;
      userMessage = "Too many requests. Please try again later.";
    } else if (statusCode >= 500) {
      code = ErrorCode.INTERNAL_SERVER_ERROR;
      userMessage = "Server error. Please try again later.";
    }

    return {
      userMessage,
      developerMessage: `HTTP ${statusCode}: ${error.statusText}`,
      code,
      statusCode,
      originalError: error,
    };
  }

  // Handle plain objects with error structure
  if (error && typeof error === "object") {
    if ("code" in error && "message" in error) {
      return {
        userMessage: error.message,
        developerMessage: error.details || error.message,
        code: error.code as ErrorCode,
        field: error.field,
        context: error.context,
        originalError: error,
      };
    }

    if ("message" in error) {
      return {
        userMessage: error.message,
        developerMessage: JSON.stringify(error, null, 2),
        code: ErrorCode.UNKNOWN_ERROR,
        originalError: error,
      };
    }
  }

  // Handle string errors
  if (typeof error === "string") {
    return {
      userMessage: error || fallbackMessage,
      developerMessage: error || fallbackMessage,
      code: ErrorCode.UNKNOWN_ERROR,
      originalError: error,
    };
  }

  // Fallback for unknown error types
  return {
    userMessage: fallbackMessage,
    developerMessage: `Unknown error type: ${typeof error}`,
    code: ErrorCode.UNKNOWN_ERROR,
    originalError: error,
  };
}

/**
 * Format error for logging to console.
 *
 * @param parsedError - The parsed error
 * @param includeContext - Whether to include context data
 */
export function formatErrorForLogging(
  parsedError: ParsedError,
  includeContext: boolean = true,
): string {
  const parts = [
    `[${parsedError.code}]`,
    `User: ${parsedError.userMessage}`,
    `Dev: ${parsedError.developerMessage}`,
  ];

  if (parsedError.field) {
    parts.push(`Field: ${parsedError.field}`);
  }

  if (includeContext && parsedError.context) {
    parts.push(`Context: ${JSON.stringify(parsedError.context, null, 2)}`);
  }

  return parts.join("\n");
}

/**
 * Check if an error code represents a user-facing error that should be shown.
 */
export function shouldShowErrorToUser(code: ErrorCode): boolean {
  // Don't show auth errors that redirect to login
  if (code === ErrorCode.AUTH_TOKEN_EXPIRED || code === ErrorCode.AUTH_TOKEN_INVALID) {
    return false;
  }

  return true;
}

/**
 * Get a user-friendly title for an error based on its code.
 */
export function getErrorTitle(code: ErrorCode): string {
  switch (code) {
    case ErrorCode.VALIDATION_ERROR:
      return "Validation Error";
    case ErrorCode.NOT_FOUND:
      return "Not Found";
    case ErrorCode.UNAUTHORIZED:
      return "Unauthorized";
    case ErrorCode.FORBIDDEN:
      return "Forbidden";
    case ErrorCode.NETWORK_ERROR:
      return "Network Error";
    case ErrorCode.DATABASE_ERROR:
    case ErrorCode.DATABASE_CONNECTION_ERROR:
      return "Database Error";
    case ErrorCode.LLM_SERVICE_UNAVAILABLE:
    case ErrorCode.LLM_API_ERROR:
      return "AI Service Error";
    case ErrorCode.INTERNAL_SERVER_ERROR:
      return "Server Error";
    default:
      return "Error";
  }
}

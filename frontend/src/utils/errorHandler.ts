/**
 * Unified error handling system for HyphaGraph frontend.
 *
 * This module provides:
 * - Error parsing from various sources (API, validation, network)
 * - User-friendly error messages with debugging information
 * - Integration with i18n for localized error messages
 */
import i18n from "../i18n";

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
  context?: Record<string, unknown>;
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
  context?: Record<string, unknown>;

  /** Original error for logging */
  originalError?: unknown;

  /** HTTP status code if applicable */
  statusCode?: number;
}

/**
 * Error instance that preserves parsed API metadata while remaining compatible
 * with existing `error.message` consumers across the UI.
 */
export class ParsedAppError extends Error implements ParsedError {
  userMessage: string;
  developerMessage: string;
  code: ErrorCode;
  field?: string;
  context?: Record<string, unknown>;
  originalError?: unknown;
  statusCode?: number;

  constructor(parsedError: ParsedError) {
    super(parsedError.userMessage);
    this.name = "ParsedAppError";
    this.userMessage = parsedError.userMessage;
    this.developerMessage = parsedError.developerMessage;
    this.code = parsedError.code;
    this.field = parsedError.field;
    this.context = parsedError.context;
    this.originalError = parsedError.originalError;
    this.statusCode = parsedError.statusCode;
  }
}

interface ValidationIssue {
  loc?: unknown[];
  msg?: string;
}

interface BackendErrorPayload {
  code: string;
  message: string;
  details?: string;
  field?: string;
  context?: Record<string, unknown>;
}

interface HttpLikeError {
  status: number;
  statusText: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isValidationIssueArray(value: unknown): value is ValidationIssue[] {
  return Array.isArray(value);
}

function isBackendErrorPayload(value: unknown): value is BackendErrorPayload {
  return isRecord(value) && typeof value.code === "string" && typeof value.message === "string";
}

function isHttpLikeError(value: unknown): value is HttpLikeError {
  return isRecord(value) && typeof value.status === "number" && typeof value.statusText === "string";
}

function getValidationField(issue: ValidationIssue): string | undefined {
  if (!Array.isArray(issue.loc)) {
    return undefined;
  }

  const path = issue.loc.filter(
    (segment): segment is string | number =>
      typeof segment === "string" || typeof segment === "number",
  );
  return path.length > 0 ? path.join(".") : undefined;
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
  error: unknown,
  fallbackMessage: string = "An unexpected error occurred",
): ParsedError {
  // If already a ParsedError, return it
  if (isRecord(error) && "userMessage" in error && "code" in error) {
    return error as ParsedError;
  }

  // Handle Error instances with structured detail
  if (error instanceof Error) {
    // Check if the error message is a JSON string (from apiFetch)
    try {
      const parsed = JSON.parse(error.message);
      if (isRecord(parsed) || isValidationIssueArray(parsed)) {
        // Backend validation error format
        if (isValidationIssueArray(parsed)) {
          const firstError = parsed[0];
          const field = firstError ? getValidationField(firstError) : undefined;
          const message = firstError?.msg ?? fallbackMessage;
          return {
            userMessage: field ? `Invalid ${field}: ${message}` : message,
            developerMessage: JSON.stringify(parsed, null, 2),
            code: ErrorCode.VALIDATION_ERROR,
            field,
            context: { validation_errors: parsed },
            originalError: error,
          };
        }

        // Backend error detail format
        if (isBackendErrorPayload(parsed)) {
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
        userMessage: i18n.t("notifications.network_error"),
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
  if (isHttpLikeError(error)) {
    const statusCode = error.status;
    let code = ErrorCode.UNKNOWN_ERROR;
    let userMessage = fallbackMessage;

    if (statusCode === 401) {
      code = ErrorCode.UNAUTHORIZED;
      userMessage = i18n.t("notifications.http_401");
    } else if (statusCode === 403) {
      code = ErrorCode.FORBIDDEN;
      userMessage = i18n.t("notifications.http_403");
    } else if (statusCode === 404) {
      code = ErrorCode.NOT_FOUND;
      userMessage = i18n.t("notifications.http_404");
    } else if (statusCode === 429) {
      code = ErrorCode.RATE_LIMIT_EXCEEDED;
      userMessage = i18n.t("notifications.rate_limit");
    } else if (statusCode >= 500) {
      code = ErrorCode.INTERNAL_SERVER_ERROR;
      userMessage = i18n.t("notifications.server_error");
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
  if (isRecord(error)) {
    if (isBackendErrorPayload(error)) {
      return {
        userMessage: error.message,
        developerMessage: error.details || error.message,
        code: error.code as ErrorCode,
        field: error.field,
        context: error.context,
        originalError: error,
      };
    }

    if (typeof error.message === "string") {
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

export function toParsedAppError(
  error: unknown,
  fallbackMessage: string = "An unexpected error occurred",
): ParsedAppError {
  if (error instanceof ParsedAppError) {
    return error;
  }

  return new ParsedAppError(parseError(error, fallbackMessage));
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
      return i18n.t("notifications.error_title_validation");
    case ErrorCode.NOT_FOUND:
      return i18n.t("notifications.error_title_not_found");
    case ErrorCode.UNAUTHORIZED:
      return i18n.t("notifications.error_title_unauthorized");
    case ErrorCode.FORBIDDEN:
      return i18n.t("notifications.error_title_forbidden");
    case ErrorCode.NETWORK_ERROR:
      return i18n.t("notifications.error_title_network");
    case ErrorCode.DATABASE_ERROR:
    case ErrorCode.DATABASE_CONNECTION_ERROR:
      return i18n.t("notifications.error_title_database");
    case ErrorCode.LLM_SERVICE_UNAVAILABLE:
    case ErrorCode.LLM_API_ERROR:
      return i18n.t("notifications.error_title_ai_service");
    case ErrorCode.INTERNAL_SERVER_ERROR:
      return i18n.t("notifications.error_title_server");
    default:
      return i18n.t("notifications.error_title_generic");
  }
}

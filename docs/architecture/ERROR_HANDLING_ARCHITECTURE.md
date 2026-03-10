# Error Handling Architecture

## Overview

HyphaGraph implements a comprehensive unified error handling system that ensures all errors—from any source—are clearly explained in the frontend with full debugging context. This document describes the architecture, data flow, and implementation details.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Error Flow](#error-flow)
4. [Error Classification](#error-classification)
5. [Implementation Details](#implementation-details)
6. [Error Recovery Strategies](#error-recovery-strategies)
7. [Performance Considerations](#performance-considerations)
8. [Security Considerations](#security-considerations)
9. [Monitoring & Observability](#monitoring--observability)

---

## Architecture Overview

### Design Principles

1. **Consistency**: All errors follow the same structure across the entire stack
2. **Context Preservation**: Errors include rich debugging information (IDs, fields, metadata)
3. **User Experience**: Clean, actionable messages for users; detailed logs for developers
4. **Type Safety**: Error codes are strongly typed enums in both Python and TypeScript
5. **Observability**: Automatic logging with full stack traces and context
6. **Recoverability**: Errors include information about whether retry is viable

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Backend (Python/FastAPI)          Frontend (TypeScript/React)      │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │  API Endpoints   │◄────HTTP────►│   API Client     │            │
│  │                  │              │   (apiFetch)     │            │
│  └────────┬─────────┘              └────────┬─────────┘            │
│           │                                 │                       │
│           ▼                                 ▼                       │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │ Error Middleware │              │  Error Parser    │            │
│  │  (Global)        │              │  (parseError)    │            │
│  └────────┬─────────┘              └────────┬─────────┘            │
│           │                                 │                       │
│           ▼                                 ▼                       │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │  ErrorResponse   │              │  ParsedError     │            │
│  │  {error:{...}}   │              │  {code, msg,...} │            │
│  └──────────────────┘              └────────┬─────────┘            │
│                                             │                       │
│                                             ▼                       │
│                                    ┌──────────────────┐            │
│                                    │  Notification    │            │
│                                    │  System          │            │
│                                    └──────────────────┘            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## System Components

### Backend Components

#### 1. Error Classes (`backend/app/utils/errors.py`)

**Purpose**: Provide structured, type-safe error definitions

**Components**:
- `ErrorCode` (Enum): 40+ standardized error codes
- `ErrorDetail` (Pydantic Model): Structured error information
- `ErrorResponse` (Pydantic Model): API response wrapper
- `AppException` (HTTPException subclass): Base exception class
- Convenience classes: `EntityNotFoundException`, `ValidationException`, etc.

**Example**:
```python
class ErrorDetail(BaseModel):
    code: ErrorCode              # Machine-readable code
    message: str                 # User-friendly message
    details: Optional[str]       # Developer details
    field: Optional[str]         # Field name for validation errors
    context: Optional[dict]      # Additional context data
```

#### 2. Error Handler Middleware (`backend/app/middleware/error_handler.py`)

**Purpose**: Catch all unhandled exceptions and convert to standardized format

**Handlers**:
- `app_exception_handler`: Handles `AppException` instances
- `validation_exception_handler`: Converts Pydantic validation errors
- `integrity_error_handler`: Converts database constraint violations
- `operational_error_handler`: Handles database connection errors
- `generic_exception_handler`: Catch-all for unexpected errors

**Flow**:
```python
try:
    # API endpoint logic
    ...
except AppException as e:
    # Already standardized → return as-is
    return ErrorResponse(error=e.error_detail)
except ValidationError as e:
    # Convert to ErrorDetail with VALIDATION_ERROR code
    return ErrorResponse(error=convert_validation_error(e))
except IntegrityError as e:
    # Parse DB error → return with DATABASE_CONSTRAINT_VIOLATION code
    return ErrorResponse(error=parse_integrity_error(e))
except Exception as e:
    # Log full traceback, return generic INTERNAL_SERVER_ERROR
    logger.exception(e)
    return ErrorResponse(error=generic_error_detail())
```

#### 3. Service Layer Error Handling

**Pattern**: Services raise `AppException` or subclasses with rich context

**Example**:
```python
# backend/app/services/entity_service.py
async def get_entity(self, db: AsyncSession, entity_id: str) -> EntityRead:
    entity = await db.get(Entity, entity_id)
    if not entity:
        raise EntityNotFoundException(
            entity_id=entity_id,
            details=f"Entity with ID '{entity_id}' does not exist"
        )
    return entity
```

**Context Enrichment**:
- Entity/Relation/Source IDs
- Field names for validation errors
- User IDs for permission errors
- File names for document errors
- PMIDs/URLs for external API errors

### Frontend Components

#### 1. Error Parser (`frontend/src/utils/errorHandler.ts`)

**Purpose**: Parse errors from any source into standardized format

**Components**:
- `ErrorCode` (enum): Synced with backend error codes
- `ParsedError` (interface): Structured error information
- `parseError()`: Universal error parser
- `formatErrorForLogging()`: Console logging formatter
- `getErrorTitle()`: User-friendly error titles

**Parsing Logic**:
```typescript
export function parseError(error: any): ParsedError {
    // 1. Already ParsedError? Return as-is
    if (error?.code && error?.userMessage) return error;

    // 2. Backend ErrorDetail structure?
    if (error?.code && error?.message) {
        return {
            userMessage: error.message,
            developerMessage: error.details || error.message,
            code: error.code,
            field: error.field,
            context: error.context
        };
    }

    // 3. Error instance with JSON message?
    try {
        const parsed = JSON.parse(error.message);
        if (parsed?.code) return parseBackendError(parsed);
    } catch {}

    // 4. Network/fetch error?
    if (isNetworkError(error)) {
        return {
            code: ErrorCode.NETWORK_ERROR,
            userMessage: "Network error",
            developerMessage: error.message
        };
    }

    // 5. Fallback to generic error
    return {
        code: ErrorCode.UNKNOWN_ERROR,
        userMessage: "An unexpected error occurred",
        developerMessage: String(error)
    };
}
```

#### 2. API Client (`frontend/src/api/client.tsx`)

**Purpose**: Automatic error parsing and logging for all API calls

**Features**:
- Parses backend error responses
- Logs full error details to console
- Handles token refresh errors
- Network error detection
- Automatic retry for 401 errors

**Error Handling Flow**:
```typescript
export async function apiFetch<T>(path: string, options: RequestInit): Promise<T> {
    try {
        const res = await fetch(`${API_BASE_URL}${path}`, options);

        if (!res.ok) {
            // Parse error response
            const errorData = await res.json();
            const backendError = errorData.error || errorData.detail;

            // Parse and log
            const parsed = parseError(backendError);
            console.error(formatErrorForLogging(parsed));

            // Throw with user message
            throw new Error(parsed.userMessage);
        }

        return res.json();
    } catch (error) {
        // Network error
        const parsed = parseError(error);
        console.error(formatErrorForLogging(parsed));
        throw error;
    }
}
```

#### 3. Notification System (`frontend/src/notifications/NotificationContext.tsx`)

**Purpose**: Display errors to users in consistent UI

**Features**:
- Accepts error objects directly (not just strings)
- Automatically parses errors via `parseError()`
- Logs full details to console
- Shows user-friendly message in toast
- Queue management with size limits (max 10)
- Auto-dismiss with configurable duration
- Severity-based styling

**Usage**:
```typescript
const { showError } = useNotification();

try {
    await createEntity(data);
} catch (error) {
    showError(error); // Automatically handles everything
}
```

**Under the Hood**:
```typescript
const showError = useCallback((messageOrError: string | Error | any) => {
    if (typeof messageOrError !== "string") {
        const parsed = parseError(messageOrError);

        // Log full details
        console.error("Error:", {
            code: parsed.code,
            userMessage: parsed.userMessage,
            developerMessage: parsed.developerMessage,
            context: parsed.context
        });

        // Show user-friendly message
        setQueue(prev => [...prev, {
            message: parsed.userMessage,
            severity: "error",
            parsedError: parsed
        }]);
    }
}, []);
```

#### 4. Error Details Component (`frontend/src/components/ErrorDetails.tsx`)

**Purpose**: Detailed error inspection for debugging

**Features**:
- Expandable accordion with all error metadata
- Displays error code, status, field, context
- Copy-to-clipboard for bug reports
- Formatted JSON display
- Syntax highlighting

**Use Cases**:
- Debug views for developers
- Error reporting UI
- Support ticket creation
- Testing/QA validation

---

## Error Flow

### Complete Error Flow Example

#### Scenario: User tries to fetch non-existent entity

**1. Frontend Request**:
```typescript
// Component
const { showError } = useNotification();

try {
    const entity = await getEntity("nonexistent-id");
} catch (error) {
    showError(error);
}
```

**2. API Call**:
```typescript
// frontend/src/api/entities.ts
export function getEntity(id: string): Promise<EntityRead> {
    return apiFetch(`/entities/${id}`);
}
```

**3. Backend Endpoint**:
```python
# backend/app/api/entities.py
@router.get("/{entity_id}")
async def get_entity(entity_id: str, db: AsyncSession = Depends(get_db)):
    entity = await entity_service.get_entity(db, entity_id)
    return entity
```

**4. Service Layer**:
```python
# backend/app/services/entity_service.py
async def get_entity(self, db: AsyncSession, entity_id: str):
    entity = await db.get(Entity, entity_id)
    if not entity:
        raise EntityNotFoundException(entity_id=entity_id)
    return entity
```

**5. Error Response** (HTTP 404):
```json
{
    "error": {
        "code": "ENTITY_NOT_FOUND",
        "message": "Entity not found",
        "details": "Entity with ID 'nonexistent-id' does not exist",
        "context": {"entity_id": "nonexistent-id"}
    }
}
```

**6. API Client Parsing**:
```typescript
// apiFetch catches error response
const errorData = await res.json();
const parsed = parseError(errorData.error);

console.error(`
[ENTITY_NOT_FOUND]
User: Entity not found
Dev: Entity with ID 'nonexistent-id' does not exist
Context: {"entity_id": "nonexistent-id"}
`);

throw new Error(parsed.userMessage);
```

**7. Component Catch Block**:
```typescript
catch (error) {
    showError(error); // Receives Error("Entity not found")
}
```

**8. Notification Display**:
- **User sees**: Toast notification - "Entity not found"
- **Console shows**: Full error with code, details, and context
- **Queue**: Added to notification queue (max 10)
- **Auto-dismiss**: After 10 seconds (error duration)

---

## Error Classification

### Error Code Categories

#### 1. Generic Errors (6 codes)
- `INTERNAL_SERVER_ERROR`: Unexpected server error
- `VALIDATION_ERROR`: Request validation failed
- `NOT_FOUND`: Generic resource not found
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions
- `RATE_LIMIT_EXCEEDED`: Too many requests

#### 2. Authentication Errors (6 codes)
- `AUTH_INVALID_CREDENTIALS`: Wrong username/password
- `AUTH_TOKEN_EXPIRED`: JWT token expired
- `AUTH_TOKEN_INVALID`: JWT token malformed/invalid
- `AUTH_EMAIL_NOT_VERIFIED`: Email verification required
- `AUTH_ACCOUNT_DEACTIVATED`: Account is deactivated
- `AUTH_INSUFFICIENT_PERMISSIONS`: Missing required permissions

#### 3. User Management (4 codes)
- `USER_EMAIL_ALREADY_EXISTS`: Email already registered
- `USER_NOT_FOUND`: User doesn't exist
- `USER_WEAK_PASSWORD`: Password doesn't meet requirements
- `USER_INVALID_EMAIL`: Email format invalid

#### 4. Entity/Relation Errors (5 codes)
- `ENTITY_NOT_FOUND`: Entity doesn't exist
- `ENTITY_SLUG_CONFLICT`: Slug already in use
- `RELATION_NOT_FOUND`: Relation doesn't exist
- `RELATION_TYPE_NOT_FOUND`: Relation type doesn't exist
- `SOURCE_NOT_FOUND`: Source doesn't exist

#### 5. LLM/Extraction Errors (6 codes)
- `LLM_SERVICE_UNAVAILABLE`: OpenAI API not configured
- `LLM_API_ERROR`: OpenAI API call failed
- `LLM_RATE_LIMIT`: OpenAI rate limit hit
- `EXTRACTION_FAILED`: LLM extraction failed
- `EXTRACTION_TEXT_TOO_LONG`: Input text exceeds limit
- `EXTRACTION_TEXT_TOO_SHORT`: Input text too short

#### 6. Document/File Errors (4 codes)
- `DOCUMENT_PARSE_ERROR`: Failed to parse document
- `DOCUMENT_TOO_LARGE`: File size exceeds limit
- `DOCUMENT_UNSUPPORTED_FORMAT`: File type not supported
- `DOCUMENT_FETCH_FAILED`: Failed to fetch external document

#### 7. Database Errors (3 codes)
- `DATABASE_ERROR`: Generic database error
- `DATABASE_CONSTRAINT_VIOLATION`: Unique/FK constraint violated
- `DATABASE_CONNECTION_ERROR`: Can't connect to database

#### 8. Business Logic Errors (6 codes)
- `INVALID_FILTER_COMBINATION`: Filter parameters invalid
- `INVALID_DATE_RANGE`: Date range invalid
- `INVALID_PAGINATION`: Pagination parameters invalid
- `MERGE_CONFLICT`: Entity merge conflict
- `CIRCULAR_RELATION_DETECTED`: Circular relationship detected

#### 9. Frontend-Only Errors (2 codes)
- `NETWORK_ERROR`: Network request failed (CORS, DNS, timeout)
- `UNKNOWN_ERROR`: Unclassified error

---

## Implementation Details

### Backend Error Handling Patterns

#### Pattern 1: Not Found Errors
```python
entity = await db.get(Entity, entity_id)
if not entity:
    raise EntityNotFoundException(
        entity_id=entity_id,
        details=f"Entity with ID '{entity_id}' does not exist in the database"
    )
```

#### Pattern 2: Validation Errors
```python
if not slug:
    raise ValidationException(
        message="Slug is required",
        field="slug",
        details="Entity slug cannot be empty",
        context={"provided_value": slug}
    )
```

#### Pattern 3: Database Constraint Errors
```python
try:
    await db.commit()
except IntegrityError as e:
    await db.rollback()
    if 'unique constraint' in str(e.orig).lower():
        raise ValidationException(
            message="Duplicate entry",
            field="slug",
            details=f"Entity with slug '{slug}' already exists",
            context={"slug": slug, "constraint": "unique_slug"}
        )
    raise
```

#### Pattern 4: External API Errors
```python
try:
    response = await client.get(url, timeout=30)
    response.raise_for_status()
except httpx.HTTPError as e:
    raise AppException(
        status_code=502,
        error_code=ErrorCode.DOCUMENT_FETCH_FAILED,
        message="Failed to fetch document",
        details=f"HTTP error: {str(e)}",
        context={"url": url, "error_type": type(e).__name__}
    )
```

#### Pattern 5: LLM Service Errors
```python
if not is_llm_available():
    raise LLMServiceUnavailableException(
        details="OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
    )

try:
    result = await llm_client.extract(text)
except LLMError as e:
    raise AppException(
        status_code=503,
        error_code=ErrorCode.LLM_API_ERROR,
        message="LLM extraction failed",
        details=str(e),
        context={"text_length": len(text)}
    )
```

#### Pattern 6: Re-raising AppExceptions
```python
try:
    result = await some_operation()
except AppException:
    # Already standardized → re-raise to preserve error details
    raise
except Exception as e:
    # Unknown error → wrap in AppException
    logger.exception("Unexpected error in operation")
    raise AppException(
        status_code=500,
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="Operation failed",
        details=str(e)
    )
```

### Frontend Error Handling Patterns

#### Pattern 1: Simple Error Display
```typescript
const { showError } = useNotification();

try {
    await createEntity(data);
} catch (error) {
    showError(error);
}
```

#### Pattern 2: Conditional Error Handling
```typescript
import { parseError, ErrorCode } from "../utils/errorHandler";

try {
    await performAction();
} catch (error) {
    const parsed = parseError(error);

    if (parsed.code === ErrorCode.UNAUTHORIZED) {
        navigate("/account");
    } else if (parsed.code === ErrorCode.LLM_SERVICE_UNAVAILABLE) {
        setShowLlmWarning(true);
    } else {
        showError(parsed.userMessage);
    }
}
```

#### Pattern 3: Form Validation Errors
```typescript
try {
    await updateEntity(id, data);
    showSuccess("Entity updated");
} catch (error) {
    const parsed = parseError(error);

    if (parsed.code === ErrorCode.VALIDATION_ERROR && parsed.field) {
        // Highlight specific form field
        setFieldError(parsed.field, parsed.userMessage);
    } else {
        showError(error);
    }
}
```

#### Pattern 4: Error Details Display
```typescript
import { ErrorDetails } from "../components/ErrorDetails";

const [error, setError] = useState<ParsedError | null>(null);

try {
    await complexOperation();
} catch (err) {
    setError(parseError(err));
}

return (
    <div>
        {error && <ErrorDetails error={error} showCopy />}
    </div>
);
```

#### Pattern 5: Silent Error Handling (Rare)
```typescript
try {
    // Background operation that doesn't require user notification
    await syncCache();
} catch (error) {
    // Log but don't show to user
    const parsed = parseError(error);
    console.warn("Cache sync failed:", parsed);
}
```

---

## Error Recovery Strategies

### Automatic Recovery

#### 1. Token Refresh (401 Errors)
- **Trigger**: HTTP 401 on non-auth endpoints
- **Strategy**: Cross-tab synchronized token refresh
- **Mechanism**: localStorage-based lock with 10s timeout
- **Retry**: Automatic retry of original request with new token
- **Fallback**: Redirect to login if refresh fails

#### 2. Rate Limit Backoff (429 Errors)
- **Trigger**: HTTP 429 or `RATE_LIMIT_EXCEEDED`
- **Strategy**: Exponential backoff (not yet implemented)
- **TODO**: Implement retry with delays: 1s, 2s, 4s, 8s

#### 3. Network Error Retry (Network Errors)
- **Trigger**: `NETWORK_ERROR` code
- **Strategy**: Manual retry by user
- **TODO**: Implement automatic retry with backoff for idempotent requests

### Manual Recovery

#### 1. User-Initiated Retry
- **UI Pattern**: Show "Retry" button on error
- **Use Case**: Transient errors (network, timeout)
- **Implementation**: Re-execute failed operation

#### 2. Alternative Path
- **UI Pattern**: Suggest alternative action
- **Example**: "Can't fetch from PubMed? Try URL import instead"
- **Use Case**: External service failures

#### 3. Partial Success Handling
- **Pattern**: Show which items succeeded/failed in batch operations
- **Example**: Bulk entity creation - show which failed and why
- **Recovery**: Allow retry of failed items only

---

## Performance Considerations

### Backend Performance

#### 1. Error Response Size
- **Optimization**: Exclude stack traces in production
- **Limit**: Context data capped at reasonable size (< 1KB)
- **Pattern**: Use error codes instead of long messages when possible

#### 2. Logging Performance
- **Strategy**: Async logging for non-critical errors
- **Pattern**: Batch logs for high-frequency errors
- **Production**: Log aggregation via external service (TODO)

#### 3. Database Rollback
- **Pattern**: Automatic rollback on IntegrityError
- **Optimization**: Use savepoints for nested transactions
- **Monitoring**: Track rollback frequency

### Frontend Performance

#### 1. Notification Queue Management
- **Limit**: Max 10 notifications in queue
- **Strategy**: Drop oldest when limit exceeded
- **Memory**: Queue cleared on component unmount

#### 2. Console Logging
- **Production**: Reduce console logging verbosity
- **Pattern**: Only log errors, not all API calls
- **TODO**: Implement log levels (ERROR, WARN, INFO, DEBUG)

#### 3. Error Parsing Optimization
- **Cache**: Frequently seen errors could be cached
- **Fast Path**: Early return for already-parsed errors
- **Lazy**: ErrorDetails component only rendered when expanded

---

## Security Considerations

### Information Disclosure Prevention

#### 1. Error Message Sanitization
- **Production**: Generic messages for INTERNAL_SERVER_ERROR
- **Development**: Full stack traces
- **Pattern**: `details` field excluded in production for 500 errors

#### 2. Database Error Masking
- **Risk**: IntegrityError messages may leak schema information
- **Mitigation**: Parse and sanitize database error messages
- **Example**: Don't expose table/column names to users

#### 3. User Enumeration Prevention
- **Pattern**: Same error for "user not found" and "wrong password"
- **Code**: `AUTH_INVALID_CREDENTIALS` (generic)
- **Timing**: Constant-time password checks (bcrypt handles this)

### Error Logging Security

#### 1. PII Redaction
- **Pattern**: Don't log passwords, tokens, or sensitive data
- **Context**: Exclude sensitive fields from error context
- **Example**: Log `{"email": "u***@example.com"}` not full email

#### 2. Error Log Access Control
- **Requirement**: Only admin users can access error logs
- **Implementation**: Audit log endpoint with superuser check
- **TODO**: Implement error log viewer UI

---

## Monitoring & Observability

### Error Metrics (TODO)

#### 1. Error Rate Tracking
- **Metric**: Errors per minute by endpoint
- **Alert**: Spike in error rate (> 10% of requests)
- **Aggregation**: By error code, endpoint, user

#### 2. Error Code Distribution
- **Visualization**: Pie chart of error codes
- **Analysis**: Identify most common failures
- **Action**: Prioritize fixes based on frequency

#### 3. User Impact Metrics
- **Metric**: Unique users affected by errors
- **Threshold**: Alert if > 5% of active users see errors
- **Correlation**: Error rate vs. user retention

### Logging Strategy

#### 1. Structured Logging
- **Format**: JSON with consistent fields
- **Fields**: `timestamp`, `level`, `error_code`, `user_id`, `endpoint`, `context`
- **Example**:
```json
{
    "timestamp": "2026-03-08T12:34:56Z",
    "level": "ERROR",
    "error_code": "ENTITY_NOT_FOUND",
    "user_id": "user-123",
    "endpoint": "/api/entities/abc",
    "context": {"entity_id": "abc"},
    "message": "Entity with ID 'abc' does not exist"
}
```

#### 2. Log Aggregation (TODO)
- **Service**: Sentry, Datadog, or CloudWatch
- **Features**: Error grouping, stack trace analysis, user impact
- **Alerts**: Configure alerts for critical errors

#### 3. Frontend Error Tracking (TODO)
- **Service**: Sentry for frontend errors
- **Data**: Browser, OS, user ID, error code, stack trace
- **Privacy**: Exclude PII from error reports

---

## Future Enhancements

### Planned Improvements

1. **Error Analytics Dashboard**
   - Visualize error rates and patterns
   - Identify error hotspots
   - Track error resolution time

2. **Automatic Error Recovery**
   - Exponential backoff for rate limits
   - Automatic retry for transient errors
   - Circuit breaker for external services

3. **Error Internationalization**
   - Translate error messages to user's language
   - Use error codes as i18n keys
   - Maintain error code consistency across languages

4. **Error Recovery Suggestions**
   - Context-aware recovery actions
   - Example: "Try again" vs "Contact support"
   - Progressive enhancement based on error type

5. **Error Correlation**
   - Link related errors across requests
   - Track error chains (A caused B caused C)
   - Root cause analysis

---

## Appendix

### Complete Error Code Reference

See `docs/development/ERROR_HANDLING_QUICK_REFERENCE.md` for the complete list of error codes and usage examples.

### Testing Error Handling

See `docs/development/TESTING_GUIDE.md` for error handling test patterns and examples.

### Error Handling Checklist

- [ ] All exceptions use AppException or subclasses
- [ ] Error codes are specific, not generic
- [ ] Context data includes relevant IDs
- [ ] User messages are actionable
- [ ] Developer messages include details
- [ ] Errors are logged with full context
- [ ] Frontend catches all async operations
- [ ] Error notifications are user-friendly
- [ ] Production errors don't leak sensitive data
- [ ] Error recovery paths are tested

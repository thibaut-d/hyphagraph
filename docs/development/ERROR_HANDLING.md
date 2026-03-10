# Unified Error Handling System

## Overview

HyphaGraph implements a unified error handling system that ensures all errors—from any source—are clearly explained and displayed in the frontend for ease of debugging.

The system consists of:

1. **Backend**: Standardized error responses with error codes and detailed messages
2. **Frontend**: Unified error parser that extracts and formats error information
3. **Integration**: Automatic error logging and notification display

## Architecture

### Backend (Python/FastAPI)

#### Error Response Format

All API errors return a standardized JSON structure:

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Entity not found",
    "details": "Entity with ID '123abc' does not exist",
    "field": null,
    "context": {
      "entity_id": "123abc"
    }
  }
}
```

**Fields:**
- `code`: Machine-readable error code (from `ErrorCode` enum)
- `message`: User-friendly message (translatable by frontend)
- `details`: Developer-friendly detailed explanation (optional)
- `field`: Field name for validation errors (optional)
- `context`: Additional context data like IDs, constraints, etc. (optional)

#### Error Codes

Defined in `backend/app/utils/errors.py::ErrorCode`:

**Generic Errors:**
- `INTERNAL_SERVER_ERROR`
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `RATE_LIMIT_EXCEEDED`

**Authentication Errors:**
- `AUTH_INVALID_CREDENTIALS`
- `AUTH_TOKEN_EXPIRED`
- `AUTH_TOKEN_INVALID`
- `AUTH_EMAIL_NOT_VERIFIED`
- `AUTH_ACCOUNT_DEACTIVATED`
- `AUTH_INSUFFICIENT_PERMISSIONS`

**User Management:**
- `USER_EMAIL_ALREADY_EXISTS`
- `USER_NOT_FOUND`
- `USER_WEAK_PASSWORD`
- `USER_INVALID_EMAIL`

**Entity/Relation Errors:**
- `ENTITY_NOT_FOUND`
- `ENTITY_SLUG_CONFLICT`
- `RELATION_NOT_FOUND`
- `RELATION_TYPE_NOT_FOUND`
- `SOURCE_NOT_FOUND`

**LLM/Extraction Errors:**
- `LLM_SERVICE_UNAVAILABLE`
- `LLM_API_ERROR`
- `LLM_RATE_LIMIT`
- `EXTRACTION_FAILED`
- `EXTRACTION_TEXT_TOO_LONG`
- `EXTRACTION_TEXT_TOO_SHORT`

**Document/File Errors:**
- `DOCUMENT_PARSE_ERROR`
- `DOCUMENT_TOO_LARGE`
- `DOCUMENT_UNSUPPORTED_FORMAT`
- `DOCUMENT_FETCH_FAILED`

**Database Errors:**
- `DATABASE_ERROR`
- `DATABASE_CONSTRAINT_VIOLATION`
- `DATABASE_CONNECTION_ERROR`

**Business Logic:**
- `INVALID_FILTER_COMBINATION`
- `INVALID_DATE_RANGE`
- `INVALID_PAGINATION`
- `MERGE_CONFLICT`
- `CIRCULAR_RELATION_DETECTED`

#### Usage in Backend Code

**Using AppException directly:**

```python
from app.utils.errors import AppException, ErrorCode
from fastapi import status

raise AppException(
    status_code=status.HTTP_404_NOT_FOUND,
    error_code=ErrorCode.ENTITY_NOT_FOUND,
    message="Entity not found",
    details=f"Entity with ID '{entity_id}' does not exist",
    context={"entity_id": entity_id}
)
```

**Using convenience exception classes:**

```python
from app.utils.errors import (
    EntityNotFoundException,
    ValidationException,
    LLMServiceUnavailableException,
)

# Entity not found
raise EntityNotFoundException(entity_id="123abc")

# Validation error
raise ValidationException(
    message="Invalid email format",
    field="email",
    details="Email must contain @ symbol"
)

# LLM unavailable
raise LLMServiceUnavailableException()
```

#### Automatic Error Handling

The global error handler middleware (`backend/app/middleware/error_handler.py`) automatically catches:

- **Pydantic validation errors** → converted to `VALIDATION_ERROR`
- **SQLAlchemy integrity errors** → converted to `DATABASE_CONSTRAINT_VIOLATION`
- **Database connection errors** → converted to `DATABASE_CONNECTION_ERROR`
- **Unhandled exceptions** → converted to `INTERNAL_SERVER_ERROR` (with full logging)

### Frontend (TypeScript/React)

#### Error Parsing

The `parseError()` function in `frontend/src/utils/errorHandler.ts` handles errors from any source:

```typescript
import { parseError } from "../utils/errorHandler";

try {
  await someApiCall();
} catch (error) {
  const parsed = parseError(error);
  console.log(parsed.userMessage);     // "Entity not found"
  console.log(parsed.developerMessage); // "Entity with ID '123abc' does not exist"
  console.log(parsed.code);            // ErrorCode.ENTITY_NOT_FOUND
  console.log(parsed.context);         // { entity_id: "123abc" }
}
```

**Handles:**
- Backend API errors with `ErrorDetail` structure
- Network errors (fetch failures, CORS, DNS)
- Validation errors (Pydantic format)
- Generic JavaScript `Error` instances
- HTTP `Response` objects
- Plain objects and strings

#### Automatic Logging

All errors are automatically logged to the console with full details when they pass through `apiFetch()`:

```typescript
// In frontend/src/api/client.tsx
const parsedError = parseError(errorData);
console.error(formatErrorForLogging(parsedError));
```

**Console output:**
```
[ENTITY_NOT_FOUND]
User: Entity not found
Dev: Entity with ID '123abc' does not exist
Context: {
  "entity_id": "123abc"
}
```

#### Notification System Integration

The notification system (`NotificationContext`) automatically handles error objects:

```typescript
import { useNotification } from "../notifications/NotificationContext";

const { showError } = useNotification();

try {
  await deleteEntity(id);
} catch (error) {
  // Automatically parses and displays user-friendly message
  showError(error);
}
```

The `showError()` method:
1. Parses the error using `parseError()`
2. Displays the **user-friendly message** in a toast notification
3. Logs the **full error details** to the console for debugging

#### Detailed Error Display

For debugging or support, use the `ErrorDetails` component:

```typescript
import { ErrorDetails } from "../components/ErrorDetails";
import { parseError } from "../utils/errorHandler";

function MyComponent() {
  const [error, setError] = useState(null);

  const handleAction = async () => {
    try {
      await someApiCall();
    } catch (err) {
      setError(parseError(err));
    }
  };

  return (
    <div>
      {error && <ErrorDetails error={error} />}
    </div>
  );
}
```

**Features:**
- Displays error code, status, field, and context
- Expandable accordion for details
- Copy button to copy full error JSON
- User-friendly formatting

## Usage Examples

### Backend: Raising Errors

```python
# api/entities.py
from app.utils.errors import EntityNotFoundException, ValidationException

@router.get("/{entity_id}")
async def get_entity(entity_id: str, db: AsyncSession = Depends(get_db)):
    entity = await entity_service.get_entity(db, entity_id)
    if not entity:
        raise EntityNotFoundException(entity_id)
    return entity

@router.post("/")
async def create_entity(data: EntityCreate, db: AsyncSession = Depends(get_db)):
    if not data.slug:
        raise ValidationException(
            message="Slug is required",
            field="slug",
            details="Entity slug cannot be empty"
        )
    # ... create entity
```

### Frontend: Handling Errors

```typescript
// In a React component
import { useNotification } from "../notifications/NotificationContext";
import { parseError } from "../utils/errorHandler";

function EntityForm() {
  const { showError, showSuccess } = useNotification();

  const handleSubmit = async (data) => {
    try {
      await createEntity(data);
      showSuccess("Entity created successfully");
    } catch (error) {
      // Automatically shows user-friendly message and logs details
      showError(error);
    }
  };

  return <form onSubmit={handleSubmit}>...</form>;
}
```

### Advanced: Custom Error Handling

```typescript
// When you need custom error handling logic
import { parseError, ErrorCode } from "../utils/errorHandler";

try {
  await fetchData();
} catch (error) {
  const parsed = parseError(error);

  if (parsed.code === ErrorCode.UNAUTHORIZED) {
    // Redirect to login
    navigate("/account");
  } else if (parsed.code === ErrorCode.LLM_SERVICE_UNAVAILABLE) {
    // Show specific UI for LLM unavailability
    setLlmUnavailable(true);
  } else {
    // Generic error handling
    showError(parsed.userMessage);
  }
}
```

## Benefits

1. **Consistency**: All errors follow the same structure across backend and frontend
2. **Debugging**: Full error details are always logged to console with context
3. **User Experience**: Users see friendly messages, not technical jargon
4. **Type Safety**: Error codes are strongly typed enums (Python & TypeScript)
5. **i18n Ready**: Error messages can be translated using error codes as keys
6. **Backwards Compatible**: Existing error strings continue to work

## Migration Guide

### Migrating Backend Code

**Before:**
```python
raise HTTPException(
    status_code=404,
    detail="Entity not found"
)
```

**After:**
```python
from app.utils.errors import EntityNotFoundException

raise EntityNotFoundException(entity_id)
```

### Migrating Frontend Code

**Before:**
```typescript
try {
  await api();
} catch (error) {
  alert(error.message);
}
```

**After:**
```typescript
import { useNotification } from "../notifications/NotificationContext";

const { showError } = useNotification();

try {
  await api();
} catch (error) {
  showError(error); // Automatically parsed and displayed
}
```

## Testing

### Backend Tests

```python
from app.utils.errors import EntityNotFoundException, ErrorCode

def test_entity_not_found_exception():
    exc = EntityNotFoundException("test-id")
    assert exc.status_code == 404
    assert exc.error_detail.code == ErrorCode.ENTITY_NOT_FOUND
    assert "test-id" in exc.error_detail.details
```

### Frontend Tests

```typescript
import { parseError, ErrorCode } from "../utils/errorHandler";

test("parses backend error structure", () => {
  const backendError = {
    code: ErrorCode.ENTITY_NOT_FOUND,
    message: "Entity not found",
    details: "Entity with ID 'abc' does not exist",
    context: { entity_id: "abc" },
  };

  const parsed = parseError(backendError);

  expect(parsed.code).toBe(ErrorCode.ENTITY_NOT_FOUND);
  expect(parsed.userMessage).toBe("Entity not found");
  expect(parsed.context?.entity_id).toBe("abc");
});
```

## Future Enhancements

- [ ] Add i18n translation files for all error codes
- [ ] Implement error tracking/monitoring (Sentry integration)
- [ ] Add error retry logic for transient failures
- [ ] Create error recovery suggestions in UI
- [ ] Add error analytics dashboard

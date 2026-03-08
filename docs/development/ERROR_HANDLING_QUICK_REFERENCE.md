# Error Handling Quick Reference

## Backend (Python)

### Raise Errors

```python
# Import
from app.utils.errors import (
    EntityNotFoundException,
    ValidationException,
    LLMServiceUnavailableException,
    AppException,
    ErrorCode
)

# Use convenience classes (RECOMMENDED)
raise EntityNotFoundException(entity_id="abc")
raise ValidationException(message="Invalid slug", field="slug")
raise LLMServiceUnavailableException()

# Or use AppException directly
raise AppException(
    status_code=404,
    error_code=ErrorCode.ENTITY_NOT_FOUND,
    message="Entity not found",
    details="Entity with ID 'abc' does not exist",
    context={"entity_id": "abc"}
)
```

### Available Convenience Classes

```python
EntityNotFoundException(entity_id: str)
RelationNotFoundException(relation_id: str)
SourceNotFoundException(source_id: str)
UnauthorizedException(message: str)
ForbiddenException(message: str)
LLMServiceUnavailableException()
ValidationException(message: str, field: str)
```

## Frontend (TypeScript)

### Handle Errors in Components

```typescript
// Import
import { useNotification } from "../notifications/NotificationContext";

// In component
const { showError, showSuccess } = useNotification();

try {
  await someApiCall();
  showSuccess("Success!");
} catch (error) {
  showError(error); // Automatically parses and displays
}
```

### Advanced Error Handling

```typescript
// Import
import { parseError, ErrorCode } from "../utils/errorHandler";

try {
  await someApiCall();
} catch (error) {
  const parsed = parseError(error);

  // Conditional logic based on error code
  if (parsed.code === ErrorCode.UNAUTHORIZED) {
    navigate("/account");
  } else if (parsed.code === ErrorCode.LLM_SERVICE_UNAVAILABLE) {
    setShowLlmWarning(true);
  } else {
    showError(parsed.userMessage);
  }
}
```

### Display Error Details

```typescript
// Import
import { ErrorDetails } from "../components/ErrorDetails";
import { parseError } from "../utils/errorHandler";

// In component
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
```

## Error Response Format

### Backend Sends

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Entity not found",
    "details": "Entity with ID 'abc' does not exist",
    "field": null,
    "context": {
      "entity_id": "abc"
    }
  }
}
```

### Frontend Receives

```typescript
interface ParsedError {
  userMessage: string;        // "Entity not found"
  developerMessage: string;   // "Entity with ID 'abc' does not exist"
  code: ErrorCode;            // ErrorCode.ENTITY_NOT_FOUND
  field?: string;             // null
  context?: Record<string, any>; // { entity_id: "abc" }
  originalError?: any;
  statusCode?: number;        // 404
}
```

## Common Error Codes

```typescript
// Authentication
ErrorCode.AUTH_INVALID_CREDENTIALS
ErrorCode.AUTH_TOKEN_EXPIRED
ErrorCode.UNAUTHORIZED

// Entities/Relations
ErrorCode.ENTITY_NOT_FOUND
ErrorCode.RELATION_NOT_FOUND
ErrorCode.SOURCE_NOT_FOUND

// LLM
ErrorCode.LLM_SERVICE_UNAVAILABLE
ErrorCode.LLM_API_ERROR
ErrorCode.EXTRACTION_FAILED

// Validation
ErrorCode.VALIDATION_ERROR

// Generic
ErrorCode.INTERNAL_SERVER_ERROR
ErrorCode.NOT_FOUND
ErrorCode.NETWORK_ERROR
```

## Console Logging

All errors are automatically logged:

```
[ENTITY_NOT_FOUND]
User: Entity not found
Dev: Entity with ID 'abc' does not exist
Context: {
  "entity_id": "abc"
}
```

## Testing

### Backend Test

```python
def test_entity_not_found():
    exc = EntityNotFoundException("test-id")
    assert exc.status_code == 404
    assert exc.error_detail.code == ErrorCode.ENTITY_NOT_FOUND
```

### Frontend Test

```typescript
test("parses error correctly", () => {
  const error = {
    code: ErrorCode.ENTITY_NOT_FOUND,
    message: "Entity not found",
    context: { entity_id: "abc" }
  };

  const parsed = parseError(error);
  expect(parsed.code).toBe(ErrorCode.ENTITY_NOT_FOUND);
  expect(parsed.userMessage).toBe("Entity not found");
});
```

## Best Practices

✅ **DO**
- Use convenience exception classes when available
- Include context data (IDs, values) in errors
- Use `showError(error)` in frontend (not `showError(error.message)`)
- Log errors to console for debugging

❌ **DON'T**
- Don't use generic `HTTPException` (use `AppException` or convenience classes)
- Don't show raw error objects to users
- Don't lose error context when re-throwing
- Don't silently swallow errors

## Migration Checklist

### Backend
- [ ] Replace `HTTPException` with `AppException` or convenience classes
- [ ] Add context data to errors
- [ ] Use appropriate error codes
- [ ] Update error messages to be user-friendly

### Frontend
- [ ] Replace `showError(error.message)` with `showError(error)`
- [ ] Add error code handling where needed
- [ ] Use `ErrorDetails` component for debugging views
- [ ] Remove manual error parsing code

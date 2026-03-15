# Unified Error Handling System - Implementation Summary

## ✅ What Has Been Implemented

A complete unified error handling system that ensures **all errors are clearly explained in the frontend, regardless of their source**, making debugging significantly easier.

## 🎯 Key Features

### 1. **Backend Standardization**
- ✅ Standardized error response format with error codes, messages, and context
- ✅ 40+ predefined error codes covering all API domains
- ✅ Convenience exception classes for common errors
- ✅ Global error handler middleware that catches all unhandled exceptions
- ✅ Automatic conversion of database, validation, and system errors

### 2. **Frontend Error Parsing**
- ✅ Universal `parseError()` function that handles errors from any source:
  - Backend API errors
  - Network errors
  - Validation errors
  - JavaScript exceptions
  - HTTP responses
- ✅ Automatic console logging with full error details
- ✅ User-friendly and developer-friendly message separation

### 3. **Notification Integration**
- ✅ Enhanced notification system that accepts error objects directly
- ✅ Automatic error parsing and display
- ✅ Full error details logged to console while showing clean UI

### 4. **Debugging Components**
- ✅ `ErrorDetails` component for detailed error inspection
- ✅ Expandable error accordion with all metadata
- ✅ Copy-to-clipboard for error reports
- ✅ Context data visualization

## 📁 Files Created

### Backend
- `backend/app/utils/errors.py` - Error codes, schemas, and exception classes
- `backend/app/middleware/error_handler.py` - Global error handling middleware
- Updated `backend/app/main.py` - Registered error handlers

### Frontend
- `frontend/src/utils/errorHandler.ts` - Error parsing and formatting utilities
- `frontend/src/components/ErrorDetails.tsx` - Error display component
- Updated `frontend/src/api/client.tsx` - Integrated error parsing
- Updated `frontend/src/notifications/NotificationContext.tsx` - Error object handling

### Documentation
- `docs/development/ERROR_HANDLING.md` - Canonical error-handling contract

## 🚀 Usage Examples

### Backend - Raising Errors

```python
# Simple usage with convenience classes
from app.utils.errors import EntityNotFoundException

raise EntityNotFoundException(entity_id="abc123")
```

**Returns to frontend:**
```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Entity not found",
    "details": "Entity with ID 'abc123' does not exist",
    "context": {"entity_id": "abc123"}
  }
}
```

### Frontend - Handling Errors

```typescript
import { useNotification } from "../notifications/NotificationContext";

const { showError } = useNotification();

try {
  await createEntity(data);
} catch (error) {
  // Automatically parses and shows user-friendly message
  // Logs full details to console
  showError(error);
}
```

**User sees:** Toast notification with "Entity not found"

**Console shows:**
```
[ENTITY_NOT_FOUND]
User: Entity not found
Dev: Entity with ID 'abc123' does not exist
Context: { "entity_id": "abc123" }
```

## 🔄 How It Works

```
┌─────────────────┐
│  Backend Error  │
│  (any source)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Error Handler Middleware│
│  - AppException         │
│  - ValidationError      │
│  - IntegrityError       │
│  - Generic Exception    │
└────────┬────────────────┘
         │
         ▼
┌───────────────────────────┐
│  Standardized JSON Format │
│  { error: { code, ... } } │
└────────┬──────────────────┘
         │
         ▼  (HTTP Response)
┌─────────────────────┐
│  apiFetch() client  │
│  - Extracts error   │
│  - Calls parseError │
│  - Logs to console  │
│  - Throws Error     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────────┐
│  Component catch block  │
│  - Calls showError()    │
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────┐
│  NotificationContext     │
│  - Parses error object   │
│  - Logs full details     │
│  - Shows user message    │
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│  User sees toast         │
│  Dev sees console logs   │
└──────────────────────────┘
```

## 🎨 Error Flow Example

1. **Backend**: User tries to fetch non-existent entity
   ```python
   raise EntityNotFoundException("missing-id")
   ```

2. **Middleware**: Converts to standard format
   ```json
   {
     "error": {
       "code": "ENTITY_NOT_FOUND",
       "message": "Entity not found",
       "details": "Entity with ID 'missing-id' does not exist",
       "context": {"entity_id": "missing-id"}
     }
   }
   ```

3. **apiFetch**: Parses response and logs
   ```typescript
   const parsedError = parseError(errorData.error);
   console.error(formatErrorForLogging(parsedError));
   throw new Error(parsedError.userMessage);
   ```

4. **Component**: Catches and displays
   ```typescript
   catch (error) {
     showError(error); // Shows "Entity not found" to user
   }
   ```

5. **Console**: Full debugging info
   ```
   [ENTITY_NOT_FOUND]
   User: Entity not found
   Dev: Entity with ID 'missing-id' does not exist
   Context: { "entity_id": "missing-id" }
   ```

## 🛡️ Error Categories Covered

- **Generic**: Internal server errors, validation, not found, unauthorized
- **Authentication**: Invalid credentials, expired tokens, unverified email
- **User Management**: Duplicate emails, weak passwords, user not found
- **Entities/Relations**: Not found, slug conflicts, type errors
- **LLM/Extraction**: Service unavailable, API errors, rate limits, text validation
- **Documents**: Parse errors, size limits, unsupported formats
- **Database**: Constraint violations, connection errors
- **Business Logic**: Invalid filters, date ranges, pagination

## 🔧 Migration Path

### No Breaking Changes
- Existing error handling continues to work
- Gradual migration is supported
- Old `HTTPException` errors are caught by middleware

### Recommended Migration
1. Replace `HTTPException` with `AppException` or convenience classes
2. Update frontend components to use `showError(error)` instead of `showError(error.message)`
3. Optionally add `ErrorDetails` component for debugging views

## 📊 Benefits Achieved

✅ **Consistency**: All errors follow the same structure
✅ **Debugging**: Full context always available in console
✅ **User Experience**: Clean, friendly error messages
✅ **Type Safety**: Error codes are enums in both Python and TypeScript
✅ **i18n Ready**: Error codes can be used as translation keys
✅ **Developer Productivity**: Less time debugging error flows
✅ **Backwards Compatible**: Existing code continues to work

## 🔍 Testing

The system automatically handles:
- ✅ Network failures → "Network error. Please check your connection."
- ✅ Validation errors → "Invalid [field]: [message]"
- ✅ Auth failures → "Unauthorized. Please log in."
- ✅ Not found → "The requested resource was not found."
- ✅ Database errors → Meaningful constraint violation messages
- ✅ LLM unavailable → "LLM service not available"
- ✅ Unknown errors → Generic message + full logging

## 📚 Next Steps

To fully adopt the system:

1. **Backend**: Gradually replace `HTTPException` with `AppException` or convenience classes
2. **Frontend**: Use `showError(error)` consistently across all components
3. **Add translations**: Create i18n files for error codes
4. **Monitor**: Add error tracking (e.g., Sentry integration)
5. **Document**: Add error codes to API documentation

## 📖 Documentation

See `docs/development/ERROR_HANDLING.md` for the canonical contract and `docs/development/ERROR_HANDLING_QUICK_REFERENCE.md` for the short operating summary.

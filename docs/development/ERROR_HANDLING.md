# Error Handling

This document defines the error-handling contract for HyphaGraph.

Keep it short, stable, and implementation-oriented. Detailed walkthroughs and tutorial-style examples do not belong here.

## Goals

- one backend error shape
- predictable frontend parsing
- user-safe messages
- developer-useful context
- loud failures instead of silent degradation

## Backend contract

API errors should resolve to one normalized shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "User-facing summary",
    "details": "Developer-facing detail",
    "field": "optional_field_name",
    "context": {}
  }
}
```

Field meaning:

- `code`: stable machine-readable identifier
- `message`: short user-facing summary
- `details`: optional developer-facing detail
- `field`: optional validation field
- `context`: optional structured debugging context

## Backend rules

- Raise structured application errors for expected failure modes.
- Convert framework, validation, and database failures into the normalized error shape.
- Log full failure context server-side.
- Do not leak secrets, raw tokens, credentials, or internal stack details in API responses.
- Use specific error codes for domain failures that the frontend may branch on.

## Frontend rules

- Parse server errors through one shared error parser.
- Show the user-facing message in notifications and UI states.
- Preserve the structured code and context for debugging.
- Do not duplicate backend error interpretation in individual views.
- Do not discard contextual information when rethrowing or wrapping errors.

## Error-code guidance

Use specific codes when the frontend or tests need stable behavior.

Prefer categories such as:

- authentication and authorization
- validation
- not found
- extraction and LLM integration
- persistence and constraint failures
- domain-specific business-rule failures

## Validation guidance

When changing error behavior, verify:

- response status
- error code
- user-facing message
- field or context when relevant
- frontend handling of the changed path

## Non-goals

This document should not contain:

- long code examples
- exhaustive lists of every error class
- implementation history
- duplicated architecture guidance

Use the codebase as the source of executable detail.

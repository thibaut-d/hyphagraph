# Error Handling Quick Reference

Use this page when you only need the operating rules.

For the contract and expectations, read `docs/development/ERROR_HANDLING.md`.

## Backend

- return the normalized `error` object
- use stable machine-readable codes
- include `field` and `context` only when they add value
- log enough context to debug the failure
- never expose secrets or internal-only details

## Frontend

- route all errors through the shared parser
- show user-facing messages, not raw objects
- keep error codes available for branching
- preserve context for debugging and support

## Tests

When error behavior changes, verify:

- HTTP status
- error code
- primary message
- frontend behavior for the affected path

## Rule of thumb

If a failure cannot be understood from its code, message, and context, the error contract is too weak.

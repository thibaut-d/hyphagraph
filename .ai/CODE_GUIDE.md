# Code Guide

This file defines the AI-agent coding defaults for HyphaGraph.

Canonical detailed references remain in:
- `docs/development/CODE_GUIDE.md`
- `docs/development/DEV_WORKFLOW.md`
- `docs/ai/AI_CONTEXT_BACKEND.md`
- `docs/ai/AI_CONTEXT_FRONTEND.md`

## Core principles

Prefer:
- explicitness over cleverness
- auditability over convenience
- boring, stable patterns over framework magic
- local reasoning over hidden behavior
- consistency with nearby code over novel structure

## Naming rules

Use names that are easy to search and review.

Prefer:
- `build_explanation_summary`
- `attach_document_revision`
- `load_relation_filters`

Avoid vague public names like:
- `process`
- `handle`
- `run`
- `data`
- `tmp`
- `res`

## Backend rules

- Keep business logic in services.
- Keep API routers thin: validate, authorize, call service, shape response.
- Use Pydantic schemas as the main I/O contract.
- Pass `user_id` where provenance matters.
- Preserve revision history instead of mutating history in place.
- Use logging, not `print()`.
- Keep auth and permission logic explicit and readable.

## Frontend rules

- Keep network behavior inside `frontend/src/api/`.
- Keep React views thin; move reusable logic into hooks/components when it improves clarity.
- Match frontend types to backend contracts.
- Route all user-visible strings through i18n when touching primary UI flows.
- Do not present computed output as unquestionable truth.
- Keep contradiction, evidence, and traceability states visible.

## Structured data preference

Prefer, in order:

1. Pydantic `BaseModel`
2. `TypedDict`
3. `dataclass`
4. raw `dict` only when unavoidable

Raw dictionaries are acceptable for:
- very local transformations
- direct library interoperability
- transient glue code that does not cross a public boundary

## Function design

Functions should be:
- focused
- typed
- understandable in isolation

Avoid:
- long multi-purpose functions
- behavior driven by many flags
- orchestration mixed with low-level implementation details

## Side effects and state

- Prefer explicit state transitions.
- Avoid hidden mutation.
- Avoid global mutable state.
- Do not silently swallow errors in domain flows.
- If degraded behavior is intentional, make it visible in code and UI.

## Testing expectations

- Add or update focused tests for behavior changes.
- Backend changes usually need pytest coverage for success and failure paths.
- Frontend changes usually need loading, error, empty, and contradiction-visible states covered when relevant.
- If you cannot run a needed test, say so clearly.

## Temporary and support artifacts

- Put temporary reports and experiments in `.temp/`.
- Keep agent workflow files in `.ai/`.
- Do not scatter scratch files into backend, frontend, or docs directories.

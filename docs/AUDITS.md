# AI Readability and Architecture Audits

This file is the concise audit entrypoint for HyphaGraph.

The detailed repository-specific audit playbook remains in:

- `audit.md`

Use this file to choose the right audit quickly, then use `audit.md` when you need the full checklist and search patterns.

## Severity levels

- Critical: risks knowledge integrity, provenance, security, or core contract correctness
- Major: significantly harms maintainability, clarity, or architectural consistency
- Minor: worth fixing, but not urgent

## Minimum audit baseline

At minimum, review:
- naming clarity
- boundary discipline
- typed contracts
- contradiction and traceability visibility
- side effects and error handling
- test coverage for changed behavior

## HyphaGraph audit categories

1. Knowledge integrity and explainability
   Check that computed outputs remain recomputable, evidence-backed, and non-authoritative.
2. Revision architecture and provenance
   Check that revision snapshots, `is_current` behavior, and `user_id` provenance remain intact.
3. Security and authentication
   Check secrets handling, explicit permissions, auth flows, and secure defaults.
4. API and service boundaries
   Check that routers stay thin, services own domain logic, and frontend networking stays in shared clients.
5. Frontend uncertainty and traceability
   Check contradiction visibility, source traceability, i18n coverage, and neutral uncertainty wording.
6. Silent error handling and logging
   Check swallowed failures, vague logging, `print()` usage, and invisible degraded states.
7. Test suite health
   Check that changed behavior is covered and the focused suites still run.
8. Typed contract discipline
   Check Pydantic usage, stable response shapes, and frontend/backend contract alignment.
9. Modularity and pattern consistency
   Check oversized files, mixed responsibilities, and one-off patterns.

## How to use this file

- For a quick audit prompt, use `docs/commands/audit.md`.
- For detailed checklists, severity framing, and search commands, use `audit.md`.
- When the audit produces durable follow-up work, record it in `TODO.md`.

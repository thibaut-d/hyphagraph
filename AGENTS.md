# Agent Instructions

HyphaGraph uses this file as the canonical AI-agent entrypoint.

Work toward changes that are correct, explicit, auditable, maintainable, and aligned with HyphaGraph's evidence-first architecture.

Read policy:

- Do not load all docs by default.
- Start with the smallest relevant context set.
- Use `docs/` as the detailed source of truth.
- If a task matches a command workflow, read the matching file in `docs/commands/`.

Default entry set:

1. `README.md`
2. `docs/architecture/ARCHITECTURE.md`
3. `docs/development/CODE_GUIDE.md`
4. `TODO.md`
5. `docs/PLANNING_GUIDE.md`

Core rules:

- documents are sources, not truth
- claims are stored, not human-authored syntheses
- contradictions must remain visible
- computed outputs must be explainable and recomputable
- LLM output is never authoritative
- revision history and user provenance must remain auditable
- prefer local, pattern-matching changes over broad rewrites
- keep business logic in backend services and shared frontend clients

Use these detailed references by task:

| Task | Read |
|------|---------------|
| Backend API or services | `docs/architecture/ARCHITECTURE.md`, `docs/development/CODE_GUIDE.md`, relevant files in `backend/app/` and `backend/tests/` |
| Frontend views or components | `docs/architecture/ARCHITECTURE.md`, `docs/development/CODE_GUIDE.md`, `docs/product/UX.md`, relevant files in `frontend/src/` |
| Database or schema changes | `docs/architecture/ARCHITECTURE.md`, `docs/architecture/DATABASE_SCHEMA.md`, relevant files in `backend/app/models/` and `backend/alembic/` |
| Inference or explanation changes | `docs/architecture/ARCHITECTURE.md`, `docs/architecture/COMPUTED_RELATIONS.md`, relevant files in `backend/app/services/`, `backend/app/schemas/`, and affected UI surfaces |
| Authentication or authorization | `docs/development/CODE_GUIDE.md`, `docs/architecture/ARCHITECTURE.md`, relevant files in `backend/app/utils/`, `backend/app/api/`, and `backend/tests/` |
| E2E changes | `docs/development/CODE_GUIDE.md`, `docs/development/E2E_TESTING_GUIDE.md`, `e2e/README.md` |
| Audit or review work | `docs/audit.md`, `TODO.md` |

Command workflows:

- `docs/commands/bootstrap.md` for session setup
- `docs/commands/implement.md` for feature work
- `docs/commands/refactor.md` for behavior-preserving cleanup
- `docs/commands/debug.md` for investigation and fixes
- `docs/commands/review.md` for review work
- `docs/commands/audit.md` for structured audits

Release gates (non-negotiable):

- **Never declare, label, tag, or otherwise call this project "v1", "v1.0", "stable", "production-ready", or any equivalent milestone** unless the user has explicitly stated both of the following in the same conversation:
  1. "I have tested it myself" (or equivalent confirmation of extensive personal hands-on testing), AND
  2. "Human review is complete" (or equivalent confirmation that a human code/UX review has been conducted).
- AI-generated test results, passing CI, and audit sign-offs do **not** satisfy these gates. They are necessary but not sufficient.
- If asked to prepare a release, cut a changelog, bump a version, or write release notes toward v1, remind the user of these gates before proceeding.

Execution notes:

- For non-trivial work, identify impacted modules, make a short plan, and state validation.
- Keep temporary notes and scratch outputs in `.temp/`.
- Use `TODO.md` as the live work log; `docs/PLANNING_GUIDE.md` explains the planning format.
- A task is done only when architecture, provenance, contradiction visibility, and validation expectations still hold.

Audit output rules:

- `TODO.md` is the single source of truth for actionable findings. Audit reports in `.temp/` are reference material only.
- After every audit, write each actionable finding as a checkbox item in `TODO.md` with: ID, file path and line number, problem statement, and concrete fix. Do not leave actionable items only in the audit report.
- Summaries and references in `ROADMAP.md` or other docs must point to `TODO.md`, never duplicate the item list.
- Mark items `[x]` in `TODO.md` as soon as they are resolved. Do not leave stale open checkboxes.

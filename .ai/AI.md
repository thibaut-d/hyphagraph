# AI Repository Instructions

HyphaGraph uses this directory as the canonical home for AI-agent guidance.

Your objective is to produce code and documentation that are:
- correct
- explicit
- auditable
- maintainable
- aligned with HyphaGraph's evidence-first architecture

Before doing substantial work, read:

1. `README.md`
2. `.ai/ARCHITECTURE.md`
3. `.ai/CODE_GUIDE.md`
4. `TODO.md`
5. `.ai/TODO.md`
6. `.ai/AUDITS.md`

If the task matches one of the available commands, also read the relevant file in `.ai/commands/`.

## Core operating rules

- Do not jump into non-trivial edits without understanding the affected module and existing pattern.
- Prefer local, minimal changes over broad rewrites.
- Reuse current backend, frontend, and test patterns before adding new structure.
- Preserve repository invariants around provenance, explainability, contradiction visibility, and LLM constraints.
- Use the architecture docs in `docs/` as canonical for domain and system behavior.

## Required project invariants

These are non-negotiable:

- documents are sources, not truth
- claims are stored, not human-authored syntheses
- contradictions must remain visible
- computed outputs must be explainable and recomputable
- LLM output is never authoritative
- revision history and user provenance must remain auditable

## What to read for common tasks

Use the smallest relevant context set.

| Task | Required docs |
|------|---------------|
| Backend API or services | `.ai/ARCHITECTURE.md`, `.ai/CODE_GUIDE.md`, `docs/ai/AI_CONTEXT_BACKEND.md` |
| Frontend views or components | `.ai/ARCHITECTURE.md`, `.ai/CODE_GUIDE.md`, `docs/ai/AI_CONTEXT_FRONTEND.md`, `docs/product/UX.md` |
| Database or schema changes | `.ai/ARCHITECTURE.md`, `docs/architecture/DATABASE_SCHEMA.md`, `docs/ai/AI_CONTEXT_BACKEND.md` |
| Inference or explanation changes | `.ai/ARCHITECTURE.md`, `docs/architecture/COMPUTED_RELATIONS.md`, `docs/ai/AI_CONTEXT_ARCHITECTURE.md` |
| Authentication or authorization | `.ai/CODE_GUIDE.md`, `docs/architecture/ARCHITECTURE.md`, `docs/ai/AI_CONTEXT_BACKEND.md` |
| E2E changes | `.ai/CODE_GUIDE.md`, `docs/development/E2E_TESTING_GUIDE.md`, `e2e/README.md` |
| Audit or review work | `.ai/AUDITS.md`, `audit.md`, `TODO.md` |

## Planning and execution

For non-trivial work:

- identify impacted modules before editing
- write a short plan
- state assumptions when they matter
- describe how the change will be validated

When editing:

- keep orchestration readable
- keep business logic in backend services, not API handlers or React views
- prefer typed contracts over ad-hoc dictionaries
- preserve existing tests or add focused coverage for behavior changes

## Temporary files

All temporary notes, debug scripts, reports, and scratch outputs belong in:

`.temp/`

Do not leave temporary artifacts in source directories.

## Session memory

`TODO.md` at the repository root is the canonical live work log and handoff file.

Update it for meaningful ongoing work when:
- starting a substantial task
- finishing a milestone
- identifying follow-up items that should survive session loss

`.ai/TODO.md` explains the planning format. The live task list stays in `TODO.md`.

## Definition of done

A task is not complete until:

- the change fits the repository architecture
- naming and types are explicit enough to review quickly
- provenance, contradiction, and explainability expectations still hold
- relevant tests or checks were run, or the blocker is stated clearly
- temporary artifacts remain confined to `.temp/`
- follow-up work is captured when needed

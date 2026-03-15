# Planning and Handoff Guide

This file defines how AI agents should plan non-trivial HyphaGraph work.

The canonical live task tracker remains:

- `TODO.md`

Use `TODO.md` for current work, carry-over tasks, and milestone notes that must survive session loss.

Use this file as the format and behavior guide for updating it.

## When to write or update a plan

Write or refresh a plan when:
- the task touches multiple files or layers
- the task affects architecture-sensitive areas
- the request is ambiguous enough that assumptions matter
- you are producing an audit or review with follow-up work

Small local fixes do not need a long plan.

## Required planning fields

For non-trivial work, capture:

- objective
- impacted modules
- assumptions
- implementation or investigation steps
- validation steps
- risks
- status

## Suggested format

```md
## Title

Short task name.

### Objective
What must be achieved.

### Impacted modules
- `backend/...`
- `frontend/...`

### Assumptions
- ...

### Plan
1. Inspect the current behavior and boundary.
2. Add or adjust tests for the intended behavior.
3. Implement the smallest safe change.
4. Re-run the focused checks.

### Validation
- pytest target(s)
- Vitest target(s)
- manual verification if needed

### Risks
- provenance regression
- frontend/backend contract drift

### Status
planned
```

## HyphaGraph-specific reminders

When planning, explicitly check whether the change affects:

- provenance or revision history
- contradiction visibility
- explainability
- auth or permissions
- backend/service boundary discipline
- typed backend/frontend contracts

If yes, include that in validation and risk notes.

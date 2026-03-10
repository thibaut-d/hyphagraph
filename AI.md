# AI Agent Entry Point

**You MUST follow these instructions at the start of every session.**

---

## Step 1 — Read these files now

Read all four files below before doing anything else:

1. **`TODO.md`** — Current work status. What is in progress, what comes next. This is your memory across sessions.
2. **`docs/ai/AI_CONTEXT_CORE.md`** — Project invariants, data model, tech stack, naming conventions, non-negotiables.
3. **`docs/product/VIBE.md`** — Your behavior rules: TDD, commit discipline, code standards, how to plan and execute.
4. **`docs/ai/AI_ROUTING_RULES.md`** — Which additional files to load depending on your task.

Do NOT start coding until you have read all four.

---

## Step 2 — Read task-specific files

After reading the above, identify your task and load the relevant files:

| Task | Read these files |
|------|-----------------|
| Database / schema changes | `docs/architecture/DATABASE_SCHEMA.md`, `docs/ai/AI_CONTEXT_BACKEND.md` |
| Inference / computed relations | `docs/architecture/COMPUTED_RELATIONS.md`, `docs/ai/AI_CONTEXT_ARCHITECTURE.md` |
| Backend API or services | `docs/ai/AI_CONTEXT_BACKEND.md` |
| Frontend views or components | `docs/ai/AI_CONTEXT_FRONTEND.md`, `docs/product/UX.md` |
| Authentication changes | `docs/ai/AI_CONTEXT_BACKEND.md`, `docs/architecture/ARCHITECTURE.md` (Section 6) |
| E2E tests | `docs/development/E2E_TESTING_GUIDE.md` |
| Architecture decisions | `docs/architecture/ARCHITECTURE.md`, `docs/ai/AI_CONTEXT_ARCHITECTURE.md` |

For detailed per-task file lists (including specific source files to load), see `docs/ai/AI_ROUTING_RULES.md`.

---

## Step 3 — Keep TODO.md updated

Throughout the session, **update `TODO.md` regularly** (after each significant step). This file is the only thing that survives a session crash. If you don't update it, progress awareness is lost.

- Remove completed items
- Keep only active work and next steps
- Keep it clean and small

---

## Reference documents (read only when needed)

| Document | When to read |
|----------|-------------|
| `PROJECT_OVERVIEW.md` | Need to understand the project vision or philosophy |
| `CONTRIBUTING.md` | Dev setup, PR guidelines |
| `docs/development/DEV_WORKFLOW.md` | Workflow phases, Docker setup, commit discipline, test commands |
| `docs/development/CODE_GUIDE.md` | Coding patterns, auth conventions, security checklist |
| `docs/product/ROADMAP.md` | Project status, what has been done, what remains |

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
| This file (`AI.md`) | Session start instructions plus AI readability, modularity, and audit requirements |

---

## AI Coding Rules

These rules must be followed whenever an AI agent generates, edits, or refactors code in this repository.

The primary objective is to produce code that is easy for humans to read, review, and maintain.

### 1. Readability First

Code must remain understandable at first glance.

Rules:

- Use clear and descriptive names for variables, functions, and classes.
- Avoid abbreviations unless they are widely known.
- Functions must remain short and focused.
- Prefer explicit code over clever or overly compact code.
- Avoid deep nesting of conditions or loops.
- A reader should understand a function's purpose in less than 10 seconds.

Bad example:

```python
def proc(x):
    ...
```

Good example:

```python
def compute_road_surface_defects(image_batch):
    ...
```

### 2. Keep Surface Code Simple

Top-level code must stay simple and readable.

The main workflow of the program should read like a high-level description of the pipeline.

Example:

```python
frames = load_frames(video)
detections = detect_objects(frames)
defects = analyze_road_surface(detections)
export_results(defects)
```

Implementation complexity must not appear at this level.

### 3. Hide Complexity in Subsystems

Complex logic must be encapsulated.

Rules:

- Move complex logic into helper functions.
- Move domain logic into dedicated modules.
- Use classes or modules to group related behaviors.
- Use clear abstractions.

Goal:

A reader should understand what happens without immediately needing to understand how it works internally.

### 4. Enforce Separation of Concerns

The codebase must clearly separate responsibilities.

Typical layers in this project may include:

- data loading
- preprocessing
- model inference
- post-processing
- metrics
- export / persistence

Rules:

- Business logic must not be mixed with IO.
- Model inference code must not contain dataset logic.
- Metrics and evaluation must be isolated.

### 5. Avoid Tight Coupling

Modules must remain independent.

Rules:

- Avoid modules importing each other in cycles.
- Prefer passing data instead of importing internal state.
- Use small interfaces between modules.

Bad example:

```text
module_a -> module_b -> module_a
```

### 6. Enforce Modularity

Large files and monolithic modules must be avoided.

Rules:

- Split large files into focused modules.
- Group related functionality.
- Each module must have a clear purpose.

Signs of poor modularity:

- files larger than about 500-800 lines
- classes doing multiple unrelated tasks
- utility functions scattered everywhere

### 7. Remove Code Duplication

Duplicated logic must be refactored.

Rules:

- Extract shared code into utilities.
- Create reusable helpers.
- Avoid copy/paste implementations.

Duplicated logic makes the system harder to evolve.

### 8. AI Audit Requirement

Before completing a task, the AI must perform a readability and architecture audit.

Steps:

1. Scan modified code for:
   - readability issues
   - structural problems
   - duplication
   - architectural violations
2. Document findings in `TODO.md`.

Each TODO item must contain:

- problem description
- location in the code
- reason it harms maintainability
- proposed refactoring

Example:

```markdown
### Refactor Needed: Tight Coupling

File: road_analysis/pipeline.py

Problem:
The pipeline directly imports internal functions from the inference module.

Why it is problematic:
This creates tight coupling between pipeline orchestration and inference implementation.

Proposed fix:
Introduce a public inference interface and remove direct internal imports.
```

### 9. Prefer Clarity Over Performance Tricks

Unless performance is critical, prefer readable code.

If an optimization reduces readability:

- document it
- isolate it
- explain the reason

### 10. Human Review Priority

The final code must always be optimized for human review.

AI-generated code should never:

- hide logic in clever constructs
- generate unnecessary abstractions
- produce overly complex patterns

If unsure, choose the simpler implementation.

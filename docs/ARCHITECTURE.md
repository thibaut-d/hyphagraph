# Architecture Guide

This file is the shared map of the HyphaGraph repository for both humans and agents.

Use it to answer:
- where code belongs
- which module owns which responsibility
- which boundaries must not be crossed
- which project constraints matter before editing

Canonical detailed references remain in:
- `docs/architecture/ARCHITECTURE.md`
- `docs/architecture/DATABASE_SCHEMA.md`
- `docs/architecture/COMPUTED_RELATIONS.md`

## Repository shape

- `backend/`
  FastAPI application, domain services, repositories, models, schemas, migrations, backend tests.
- `frontend/`
  React and TypeScript application, typed API clients, views, reusable components, Vitest tests.
- `e2e/`
  Playwright suite for end-to-end flows.
- `docs/architecture/`
  Canonical system design, database schema, inference model, and architectural constraints.
- `docs/development/`
  Workflow, code standards, and testing guides.
- `docs/product/`
  UX principles, roadmap, and product-facing constraints.
- `AGENTS.md` and `docs/`
  AI-agent entrypoint, coding guidance, commands, and audit summaries.
- `.temp/`
  Temporary audit reports, scratch outputs, and experiment artifacts.

## What to open

Use the shared docs first, then the owning code.

| Task | Open |
|------|------|
| Backend API or services | `docs/CODE_GUIDE.md`, relevant files in `backend/app/api/`, `backend/app/services/`, `backend/app/schemas/`, `backend/tests/` |
| Frontend views or components | `docs/CODE_GUIDE.md`, `docs/product/UX.md`, relevant files in `frontend/src/views/`, `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/api/` |
| Database or schema changes | `docs/architecture/DATABASE_SCHEMA.md`, relevant files in `backend/app/models/`, `backend/alembic/`, `backend/tests/` |
| Inference or explanation changes | `docs/architecture/COMPUTED_RELATIONS.md`, relevant files in `backend/app/services/`, `backend/app/schemas/`, `frontend/src/views/`, `frontend/src/components/` |
| Authentication or authorization | `docs/development/CODE_GUIDE.md`, relevant files in `backend/app/utils/`, `backend/app/api/`, `backend/tests/` |
| E2E work | `docs/development/E2E_TESTING_GUIDE.md`, relevant files in `e2e/tests/`, `e2e/fixtures/`, `e2e/playwright.config.ts` |

## Backend shape

- `backend/app/api/`: request validation, auth, response shaping
- `backend/app/services/`: domain logic and orchestration
- `backend/app/repositories/`: persistence queries
- `backend/app/schemas/`: I/O contracts
- `backend/app/models/`: ORM models
- `backend/app/utils/`: focused helpers
- `backend/tests/`: backend behavior coverage

## Frontend shape

- `frontend/src/api/`: shared network clients
- `frontend/src/views/`: route-level screens
- `frontend/src/components/`: reusable UI building blocks
- `frontend/src/hooks/`: reusable stateful logic
- `frontend/src/types/`: frontend contract types
- `frontend/src/i18n/`: user-visible strings
- `frontend/tests/` and `frontend/src/**/__tests__/`: frontend behavior coverage

## Ownership and boundaries

### Backend

The backend owns:
- authoritative validation
- domain logic
- provenance recording
- inference and explanation behavior
- API contracts

The backend must not:
- let API routers absorb business logic
- store human-authored syntheses as facts
- let LLM-generated output become authoritative

### Frontend

The frontend owns:
- presentation
- editing workflows
- navigation
- evidence display
- uncertainty and contradiction visibility

The frontend must not:
- duplicate backend reasoning
- hide contradictions or missing evidence
- bypass shared API clients with one-off network logic

### Database and revisions

PostgreSQL is the source of truth.

Mutable domain objects follow revision architecture:
- immutable base records
- current revision snapshot
- historical revisions retained
- user provenance preserved when available

Schema changes must preserve revision and provenance rules.

## Preferred data flow

Use explicit, typed flows:

`request boundary -> schema -> service -> repository/domain logic -> schema/result -> boundary`

Avoid:
- raw nested dict contracts across module boundaries
- frontend business logic that recreates backend decisions
- cross-layer shortcuts
- hidden state or implicit mutation

## Project-specific extension rules

When adding or changing features:

1. identify the owner module first
2. follow adjacent file patterns before inventing a new abstraction
3. keep top-level orchestration readable
4. push low-level complexity into focused helpers or services
5. preserve traceability from computed output back to sources

## High-risk areas

Treat changes in these areas as architecture-sensitive:

- inference and explanation services
- revision write paths
- auth and permissions
- extraction or review flows
- synthesis, disagreement, and evidence UI
- shared API client behavior

These areas usually need focused tests and a more explicit review of invariants.

# Architecture Guide

This file is the AI-oriented map of the HyphaGraph repository.

Use it to answer:
- where code belongs
- which module owns which responsibility
- which boundaries must not be crossed
- which project constraints matter before editing

Canonical detailed references remain in:
- `docs/architecture/ARCHITECTURE.md`
- `docs/architecture/DATABASE_SCHEMA.md`
- `docs/architecture/COMPUTED_RELATIONS.md`
- `docs/ai/AI_CONTEXT_*.md`

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
- `.ai/`
  AI-agent entrypoint, coding guidance, commands, and audit summaries.
- `.temp/`
  Temporary audit reports, scratch outputs, and experiment artifacts.

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

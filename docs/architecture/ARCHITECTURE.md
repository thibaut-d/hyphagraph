# Architecture

## Repository Map

Quick reference for navigating the codebase.

### Directory shape

- `backend/` — FastAPI application, domain services, repositories, models, schemas, migrations, backend tests.
- `frontend/` — React/TypeScript application, typed API clients, views, reusable components, Vitest tests.
- `e2e/` — Playwright end-to-end suite.
- `docs/architecture/` — Canonical system design, database schema, inference model, and architectural constraints.
- `docs/development/` — Workflow, code standards, and testing guides.
- `docs/product/` — UX principles, roadmap, and product-facing constraints.
- `.temp/` — Temporary audit reports, scratch outputs, and experiment artifacts.

### What to open by task

| Task | Open |
|------|------|
| Backend API or services | `docs/development/CODE_GUIDE.md`, files in `backend/app/api/`, `backend/app/services/`, `backend/app/schemas/`, `backend/tests/` |
| Frontend views or components | `docs/development/CODE_GUIDE.md`, `docs/product/UX.md`, files in `frontend/src/views/`, `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/api/` |
| Database or schema changes | `docs/architecture/DATABASE_SCHEMA.md`, files in `backend/app/models/`, `backend/alembic/`, `backend/tests/` |
| Inference or explanation changes | `docs/architecture/COMPUTED_RELATIONS.md`, files in `backend/app/services/`, `backend/app/schemas/`, `frontend/src/views/`, `frontend/src/components/` |
| Authentication or authorization | `docs/development/CODE_GUIDE.md`, files in `backend/app/utils/`, `backend/app/api/`, `backend/tests/` |
| E2E work | `docs/development/E2E_TESTING_GUIDE.md`, files in `e2e/tests/`, `e2e/fixtures/`, `e2e/playwright.config.ts` |

### Backend module ownership

- `backend/app/api/` — request validation, auth, response shaping
- `backend/app/services/` — domain logic and orchestration
- `backend/app/repositories/` — persistence queries
- `backend/app/schemas/` — I/O contracts
- `backend/app/models/` — ORM models
- `backend/app/utils/` — focused helpers
- `backend/tests/` — backend behavior coverage

### Frontend module ownership

- `frontend/src/api/` — shared network clients
- `frontend/src/views/` — route-level screens
- `frontend/src/components/` — reusable UI building blocks
- `frontend/src/hooks/` — reusable stateful logic
- `frontend/src/types/` — frontend contract types
- `frontend/src/i18n/` — user-visible strings

### Ownership boundaries

**Backend owns**: authoritative validation, domain logic, provenance recording, inference and explanation behavior, API contracts.
**Backend must not**: let API routers absorb business logic; store human-authored or LLM-generated syntheses as facts.

**Frontend owns**: presentation, editing workflows, navigation, evidence display, uncertainty and contradiction visibility.
**Frontend must not**: duplicate backend reasoning; hide contradictions; bypass shared API clients with one-off network logic.

### Preferred data flow

```
request boundary → schema → service → repository/domain logic → schema/result → boundary
```

Avoid raw nested dict contracts across module boundaries, frontend logic that recreates backend decisions, or cross-layer shortcuts.

### High-risk areas

Treat changes in these areas as architecture-sensitive — they need focused tests and explicit invariant review:

- inference and explanation services
- revision write paths
- auth and permissions
- extraction or review flows
- synthesis, disagreement, and evidence UI
- shared API client behavior

---

This document describes the **system architecture** of HyphaGraph.

It focuses on:
- component responsibilities
- data flows
- architectural choices
- non-negotiable constraints

It intentionally avoids:
- database schema definitions (see `DATABASE_SCHEMA.md` in this directory)
- philosophical or scientific motivation (see `../../PROJECT_OVERVIEW.md`)

---

## 1. Architectural Intent

The architecture ensures that:

- document-grounded relations are the only source of facts
- contradictions are preserved, not hidden
- syntheses are always computable and explainable
- AI components are constrained and replaceable
- no component becomes epistemically authoritative

The system favors **clarity, auditability, and determinism** over cleverness.

---

## 2. High-Level System Overview

```
┌──────────────┐
│  Documents   │
│ (PDF, HTML)  │
└──────┬───────┘
       │
       ▼
┌────────────────────┐
│ Ingestion &        │
│ Relation Extraction│◄── Human or LLM
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│     FastAPI        │
│  Domain Services   │◄── Frontend (React)
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   PostgreSQL       │
│ Source of Truth    │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Inference &       │
│  Aggregation       │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Explanation &      │
│ LLM Formatting     │
└────────────────────┘
```

---

## 3. Core Components and Responsibilities

### 3.1 PostgreSQL — Source of Truth

Stores all **authoritative data**: sources, entities, relations, roles, cached inference artifacts.

- Strong transactional guarantees
- Explicit constraints and auditability
- No other system may introduce new semantics

### 3.2 FastAPI — Domain Boundary

Acts as the **domain boundary and orchestrator**:
- Input validation (human and AI)
- Invariant enforcement
- Domain service orchestration

FastAPI does **not**: perform inference implicitly, store syntheses as facts, embed domain logic in controllers.

### 3.3 Domain Services

All **reasoning and aggregation logic**:
- Deterministic, side-effect free, recomputable, testable in isolation
- Services never mutate base relations

### 3.4 LLM Integration

Integrated as **stateless, non-authoritative workers**:
- Allowed: document parsing, relation extraction, terminology normalization, explanation formatting
- Disallowed: reasoning, consensus building, contradiction resolution, fact storage
- LLMs never write directly to the database

### 3.5 Frontend (React)

A **presentation and editing layer**:
- Document ingestion, relation review, visualization of computed outputs, evidence traceability
- Cannot override backend logic, hide uncertainty, or introduce implicit conclusions

---

## 4. Data Flow Lifecycle

### 4.1 Ingestion

1. A document is registered
2. Relations are extracted (human or LLM-assisted)
3. Relations are validated against invariants
4. Relations are stored immutably

### 4.2 Inference

1. A query defines a scope
2. Matching relations are retrieved
3. Aggregation and inference rules are applied
4. Results are produced (optionally cached)

All inferred outputs must be recomputable.

### 4.3 Explanation

For any computed output, the system can expose:
- contributing relations
- weights and rules applied
- uncertainty and contradictions

Explainability is mandatory, not optional.

---

## 5. Architectural Invariants

These constraints must always hold:

- No human-written synthesis is stored
- No LLM-generated output is authoritative
- Relations are immutable in meaning
- All conclusions must be explainable
- Hidden certainty is considered a bug

Violating these invariants is a design error.

---

## 6. Authentication & Authorization

HyphaGraph uses a **custom, explicit JWT-based authentication system**.

### Design Rationale

We do NOT use FastAPI Users or similar frameworks because:
- FastAPI Users is in maintenance mode
- Authentication is security-critical and must be fully transparent
- Framework abstractions introduce coupling and hidden complexity

### Authentication Architecture

- **User model**: id, email, hashed_password, is_active, is_superuser, created_at
- **JWT flow**: OAuth2 password flow, access + refresh tokens
- **Libraries**: passlib[bcrypt] (async via thread pool), python-jose
- **Endpoints**: POST `/auth/register`, POST `/auth/login`, GET `/auth/me`
- **Integration**: `get_current_user` dependency, explicit `user_id` for provenance

### Authorization Strategy

Authorization stays explicit in Python code. Avoid decorator-heavy or framework-managed permission systems.

See `docs/development/CODE_GUIDE.md` for the operating rules.

---

## 7. Extension Points

- **TypeDB** (planned): Secondary reasoning engine for role-based inference and contradiction detection. Operates on projections from PostgreSQL, disposable.
- **Graph engines** (Neo4j etc.): Strictly derived views for exploration and visualization. No original semantics.
- **Analytical engines** (DuckDB, Parquet): Offline analysis and benchmarking. Do not replace PostgreSQL.

---

## 8. Guiding Rule

> **If a result cannot be recomputed and explained,
> it does not belong in the system.**

This rule overrides all architectural decisions.

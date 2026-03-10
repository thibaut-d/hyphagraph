# Architecture

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

- document-grounded claims are the only source of facts
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
│ Claim Extraction   │◄── Human or LLM
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
- Services never mutate base claims

### 3.4 LLM Integration

Integrated as **stateless, non-authoritative workers**:
- Allowed: document parsing, claim extraction, terminology normalization, explanation formatting
- Disallowed: reasoning, consensus building, contradiction resolution, fact storage
- LLMs never write directly to the database

### 3.5 Frontend (React)

A **presentation and editing layer**:
- Document ingestion, claim review, visualization of computed outputs, evidence traceability
- Cannot override backend logic, hide uncertainty, or introduce implicit conclusions

---

## 4. Data Flow Lifecycle

### 4.1 Ingestion

1. A document is registered
2. Claims are extracted (human or LLM-assisted)
3. Claims are validated against invariants
4. Claims are stored immutably

### 4.2 Inference

1. A query defines a scope
2. Matching claims are retrieved
3. Aggregation and inference rules are applied
4. Results are produced (optionally cached)

All inferred outputs must be recomputable.

### 4.3 Explanation

For any computed output, the system can expose:
- contributing claims
- weights and rules applied
- uncertainty and contradictions

Explainability is mandatory, not optional.

---

## 5. Architectural Invariants

These constraints must always hold:

- No human-written synthesis is stored
- No LLM-generated output is authoritative
- Claims are immutable in meaning
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

Explicit Python functions, no RBAC frameworks:

```python
def can_create_entity(user: User) -> bool:
    return user.is_active

def can_edit_relation(user: User, relation: Relation) -> bool:
    return user.is_active and (user.is_superuser or relation.created_by_user_id == user.id)
```

See `docs/development/CODE_GUIDE.md` for full auth patterns.

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

# Architecture

This document describes the **system architecture** of HyphaGraph.

It focuses on:
- component responsibilities
- data flows
- architectural choices
- non-negotiable constraints

It intentionally avoids:
- database schema definitions (see `DATABASE_SCHEMA.md`)
- philosophical or scientific motivation (see `PROJECT.md`)

---

## 1. Architectural intent

The architecture is designed to ensure that:

- document-grounded claims are the only source of facts
- contradictions are preserved, not hidden
- syntheses are always computable and explainable
- AI components are constrained and replaceable
- no component becomes epistemically authoritative

The system favors **clarity, auditability, and determinism** over cleverness.

---

## 2. High-level system overview

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

## 3. Core components and responsibilities

### 3.1 PostgreSQL — Source of truth

PostgreSQL stores all **authoritative data**:

- sources (documents)
- entities
- relations (claims)
- roles
- optional cached inference artifacts

Design rationale:
- strong transactional guarantees
- explicit constraints
- auditability
- predictable performance

No other system may introduce new semantics.

---

### 3.2 FastAPI — Domain boundary

FastAPI acts as the **domain boundary and orchestrator**.

Responsibilities:
- input validation (human and AI)
- invariant enforcement
- domain service orchestration
- deterministic APIs

FastAPI does **not**:
- perform inference implicitly
- store syntheses as facts
- embed domain logic in controllers

---

### 3.3 Domain services

Domain services implement all **reasoning and aggregation logic**.

Characteristics:
- deterministic
- side-effect free
- recomputable
- testable in isolation

Typical responsibilities:
- scope resolution
- claim filtering
- weighting and aggregation
- uncertainty computation
- traceability generation

Services never mutate base claims.

---

### 3.4 LLM integration

LLMs are integrated as **stateless, non-authoritative workers**.

Allowed usage:
- document parsing
- claim extraction
- terminology normalization
- explanation and formatting of computed outputs

Disallowed usage:
- reasoning
- consensus building
- contradiction resolution
- fact storage

LLMs never write directly to the database.

---

### 3.5 Frontend (React)

The frontend is a **presentation and editing layer**.

Responsibilities:
- document ingestion
- claim review and correction
- visualization of computed outputs
- evidence traceability

The frontend cannot:
- override backend logic
- hide uncertainty
- introduce implicit conclusions

---

## 4. Data flow lifecycle

### 4.1 Ingestion

1. A document is registered
2. Claims are extracted (human or LLM-assisted)
3. Claims are validated against invariants
4. Claims are stored immutably

At this stage, no synthesis exists.

---

### 4.2 Inference

1. A query defines a scope
2. Matching claims are retrieved
3. Aggregation and inference rules are applied
4. Results are produced (optionally cached)

All inferred outputs must be recomputable.

---

### 4.3 Explanation

For any computed output, the system can expose:
- contributing claims
- weights and rules applied
- uncertainty and contradictions

Explainability is mandatory, not optional.

---

## 5. Architectural invariants

These constraints must always hold:

- No human-written synthesis is stored
- No LLM-generated output is authoritative
- Claims are immutable in meaning
- All conclusions must be explainable
- Hidden certainty is considered a bug

Violating these invariants is a design error.

---

## 6. Authentication & Authorization

HyphaGraph uses a **custom, explicit JWT-based authentication system** instead of third-party authentication frameworks.

### 6.1 Design rationale

We do NOT use FastAPI Users or similar frameworks because:
- FastAPI Users is in maintenance mode
- We prefer explicit, auditable authentication logic
- Framework abstractions introduce coupling and hidden complexity
- Authentication is security-critical and must be fully transparent

### 6.2 Authentication architecture

**User model (minimal):**
- id: UUID (primary key)
- email: str (unique)
- hashed_password: str
- is_active: bool
- is_superuser: bool
- created_at: datetime

No premature role systems or unnecessary fields.

**JWT-based flow:**
- OAuth2 password flow (standard FastAPI pattern)
- Access tokens only (no refresh tokens unless explicitly justified)
- Token signing with python-jose
- Password hashing with passlib[bcrypt]

**Key endpoints:**
- POST /auth/register - create new user
- POST /auth/login - obtain JWT access token
- GET /auth/me - get current user info

**Integration:**
- `get_current_user` dependency for protected endpoints
- Explicit user_id passed to services for provenance tracking
- User information stored in EntityRevision.created_by_user_id, etc.

### 6.3 Authorization strategy

**Explicit over magical:**
- No role-based access control (RBAC) frameworks
- No permission inheritance systems
- Authorization implemented as readable Python functions

**Permission helper pattern:**
```python
def can_create_entity(user: User) -> bool:
    return user.is_active

def can_edit_relation(user: User, relation: Relation) -> bool:
    return user.is_active and (user.is_superuser or relation.created_by_user_id == user.id)

def can_publish_inference(user: User) -> bool:
    return user.is_active and user.is_superuser
```

**Integration with provenance:**
- All create operations accept optional user_id parameter
- Revision system tracks who created what
- User information enables audit trails and attribution

**Security constraints:**
- Authentication logic isolated in dedicated module
- No tight coupling between auth and domain models
- Authorization checks explicit at API boundary
- Permission logic testable in isolation

### 6.4 Non-goals

We explicitly do NOT implement:
- OAuth providers (Google, GitHub, etc.)
- Organization or multi-tenant logic
- Complex role hierarchies
- Permission frameworks

These may be added later if clearly justified, but the default is simplicity.

---

## 7. Extension points

### 7.1 Reasoning engines (TypeDB)

TypeDB may be used as a **secondary reasoning engine** for:
- explicit role-based inference
- logical rule evaluation
- contradiction detection

It operates on projections from PostgreSQL and is disposable.

---

### 7.2 Graph engines (Neo4j, etc.)

Graph databases may be used for:
- exploration
- visualization
- graph algorithms

They are strictly derived views and contain no original semantics.

---

### 7.3 Analytical engines

Engines such as DuckDB or Parquet may be used for:
- large-scale aggregation
- benchmarking
- offline analysis

They do not replace PostgreSQL.

---

## 8. Guiding rule

> **If a result cannot be recomputed and explained,
> it does not belong in the system.**

This rule overrides all architectural decisions.


# System architecture & design rationale

This document describes the **global architecture** of the project:
- components
- data flows
- responsibilities
- design constraints

The architecture is designed to enforce **epistemic safety by construction**:
invalid knowledge states should be **hard or impossible to represent**.

---

## 1. Architectural goals

This system is designed to:

1. Model **document-based assertions**, not opinions
2. Preserve **context and contradiction**
3. Enable **computed (not authored) syntheses**
4. Reduce **LLM hallucinations**
5. Minimize **energy and compute costs**
6. Remain **domain-agnostic**

These goals directly drive the architectural choices below.

---

## 2. High-level architecture

```
            ┌─────────────────────┐
            │      Documents      │
            │ (PDF, text, HTML)   │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  Assertion Extract  │
            │  (Human or LLM)     │
            └─────────┬───────────┘
                      │
                      ▼
┌──────────────┐        ┌─────────────────────┐
│   Frontend   │◀──────│     FastAPI API     │
│   (React)    │        │  Domain Services    │
└──────────────┘        └─────────┬───────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │     PostgreSQL      │
                       │  Hypergraph store   │
                       └─────────┬───────────┘
                                 │
                                 ▼
                       ┌─────────────────────┐
                       │ Derived Claims &    │
                       │ Aggregation Engine  │
                       └─────────┬───────────┘
                                 │
                                 ▼
                       ┌─────────────────────┐
                       │   Explanation /     │
                       │   LLM Formatting    │
                       └─────────────────────┘

```

---

## 3. Core components

### 3.1 PostgreSQL — Source of truth

PostgreSQL is the **single source of truth**.

It stores:
- documents
- concepts
- assertions (hyper-edges)
- incidence tables
- optional cached derived claims

Why PostgreSQL:
- strong referential integrity
- transactional safety
- auditable history
- efficient analytical joins
- deterministic behavior

Graph databases are *not* used as primary storage.

---

### 3.2 Hypergraph representation

The hypergraph is implemented explicitly using relational tables:

- `assertion` represents a hyper-edge
- `assertion_concept` represents hyper-edge incidence
- roles encode semantic meaning

There is **no implicit graph logic**.
All semantics are explicit and inspectable.

---

### 3.3 FastAPI — Domain boundary

FastAPI acts as the **epistemic gatekeeper**.

Responsibilities:
- validate inputs (human or AI)
- enforce invariants
- expose deterministic APIs
- orchestrate domain services

FastAPI does **not**:
- write syntheses
- decide consensus
- embed reasoning logic in routes

All reasoning lives in services.

---

### 3.4 Domain services

Domain services implement:
- aggregation
- scoring
- contextual filtering
- explainability

Characteristics:
- deterministic
- side-effect free
- reproducible
- testable in isolation

Services never modify base assertions.

---

### 3.5 Frontend (React)

The frontend is a **presentation and editing layer**.

Responsibilities:
- document ingestion
- assertion editing and review
- visualization of derived claims
- traceability and explanation UI

The frontend is **never authoritative**.
It cannot hide uncertainty or override backend logic.

---

### 3.6 LLM integration layer

LLMs are integrated as **stateless workers**.

They are used for:
- document parsing
- assertion extraction
- terminology normalization
- explanation and summarization of computed results

They are **not** used for:
- reasoning
- consensus building
- contradiction resolution

LLMs never persist knowledge directly.

---

## 4. Data flow lifecycle

### 4.1 Ingestion

1. A document is registered
2. Assertions are created:
   - manually
   - or via LLM-assisted extraction
3. Assertions are validated
4. Assertions are stored immutably

At this stage, **no synthesis exists**.

---

### 4.2 Aggregation

1. A query defines a scope (set of concepts + roles)
2. Matching assertions are retrieved
3. Aggregation rules are applied:
   - weighting
   - grouping
   - uncertainty estimation
4. A derived claim is produced (optionally cached)

Derived claims can always be recomputed.

---

### 4.3 Explanation

For any derived claim, the system can produce:
- contributing assertions
- weights and scores
- aggregation rules used
- uncertainty metrics

This is mandatory for trust and auditability.

---

## 5. Architectural invariants (non-negotiable)

### 5.1 No synthesis persistence

- No human-written synthesis is stored
- No LLM-generated conclusion is authoritative
- Only assertions and computable artifacts exist

---

### 5.2 Assertion immutability

Assertions:
- belong to exactly one document
- do not change meaning over time
- may only be corrected for factual errors

---

### 5.3 Explicit uncertainty

Every derived output must:
- expose uncertainty
- expose evidence distribution
- expose contradiction when present

Hidden certainty is a bug.

---

## 6. Extensibility strategy

### 6.1 Graph databases (Neo4j, etc.)

Graph engines may be added for:
- exploration
- visualization
- graph algorithms

They must:
- be projections from PostgreSQL
- contain no original semantics
- be disposable

---

### 6.2 Analytical engines (DuckDB, Parquet)

Analytical engines may be used for:
- large-scale aggregation
- benchmarking
- offline analysis

They do not replace PostgreSQL.

---

### 6.3 Domain expansion

New domains must:
- reuse the same primitives
- express complexity via assertions
- avoid schema forks

The architecture is intentionally domain-agnostic.

---

## 7. Why this architecture matters

This architecture ensures that:

- Knowledge is **explicit**
- Reasoning is **auditable**
- AI is **constrained**
- Costs are **controlled**
- Contradictions are **first-class**

It is designed not to be impressive,
but to be **reliable, explainable, and scalable**.

---

## 8. Guiding architectural principle

> **If a conclusion cannot be recomputed and explained,
> it does not belong in the system.**

This principle overrides all others.


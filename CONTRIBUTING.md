# Codebase conventions & invariants

This document defines **how to write code in this repository**.

It is **not** a guide for contributing data or evidence.
It is a guide for developers working on:
- backend (FastAPI)
- database schema (PostgreSQL)
- frontend (React)
- LLM integration

The purpose of this codebase is to **enforce epistemic constraints by design**.
The code must make invalid knowledge states **impossible or explicit**.

---

## 1. Core architectural invariant

### 1.1 Single source of truth

PostgreSQL is the **only source of truth**.

- No derived knowledge is authoritative
- No synthesis is persisted as ground truth
- Any cached or computed value must be reproducible

If a value cannot be recomputed from base assertions, it must not be stored.

---

## 2. Backend (FastAPI)

### 2.1 Layered architecture (mandatory)

The backend MUST follow this separation:

```

api/        # HTTP layer (validation, auth, serialization)
services/   # domain logic (assertions, aggregation, scoring)
models/     # ORM models (no logic)
schemas/    # Pydantic models (input/output validation)
repos/      # database access only

```

Rules:
- API layer contains **no domain logic**
- ORM models contain **no business logic**
- Services do **not** perform HTTP or serialization
- Repos do **not** perform computation

---

### 2.2 Assertions are write-once

`Assertion` objects are:
- immutable in meaning
- editable only for factual corrections

Forbidden:
- mutating an assertion to reflect consensus
- reusing an assertion for another document
- updating assertions during aggregation

Aggregation MUST create **new derived objects**, never modify base assertions.

---

### 2.3 Derived data must be explicit

Any computation that:
- aggregates assertions
- scores evidence
- resolves context

MUST:
- live in `services/`
- have deterministic inputs
- expose an `explain()` method or equivalent
- be fully reproducible

No hidden logic in SQL views or frontend code.

---

## 3. Database rules (PostgreSQL)

### 3.1 Hypergraph representation

The hypergraph is implemented via **incidence tables**, not graph magic.

Mandatory tables:
- `document`
- `concept`
- `assertion`
- `assertion_concept`

Rules:
- No JSON blobs encoding logic
- No polymorphic hacks hiding relationships
- Roles must be explicit columns, not inferred

If a relation is implicit, it is a bug.

---

### 3.2 Referential integrity is mandatory

- Foreign keys MUST be enforced
- Cascades MUST be explicit
- Orphan assertions are forbidden

The database must reject invalid epistemic states.

---

## 4. Frontend (React)

### 4.1 Frontend is never authoritative

The frontend:
- displays data
- edits raw entities (documents, assertions)
- visualizes derived claims

The frontend MUST NOT:
- compute evidence scores
- resolve contradictions
- decide consensus
- hide uncertainty

If logic affects meaning, it belongs in the backend.

---

### 4.2 Explicit uncertainty in UI

Any UI component displaying a synthesis MUST:
- show uncertainty
- show confidence level
- provide access to contributing assertions

If uncertainty is not visible, the UI is incorrect.

---

## 5. LLM integration

### 5.1 LLMs are stateless workers

LLMs:
- do not own memory
- do not store knowledge
- do not persist conclusions

They operate as pure functions:

```

(document) → structured assertions
(data) → formatted explanation

```

No chain-of-thought storage.
No autonomous reasoning loops.

---

### 5.2 LLM output validation

All LLM outputs MUST:
- pass Pydantic validation
- reference a document ID
- be human-reviewable

Invalid LLM output must fail fast.

---

## 6. Testing philosophy

### 6.1 What we test

Mandatory tests:
- assertion immutability
- aggregation reproducibility
- contradiction preservation
- explainability paths

We test **invariants**, not just endpoints.

---

### 6.2 What we do NOT test

We do NOT test:
- whether a conclusion is correct
- whether evidence is convincing

This system tests **structure**, not truth.

---

## 7. Performance & scalability rules

### 7.1 No repeated synthesis

- Documents are parsed once
- Assertions are created once
- Aggregation is cached if needed

If the same synthesis is recomputed per request, it is a performance bug.

---

### 7.2 Prefer computation over generation

If a result can be computed symbolically, do not use an LLM.

LLMs are:
- expensive
- probabilistic
- non-deterministic

Use them last.

---

## 8. Extensibility rules

### 8.1 Graph engines (Neo4j, etc.)

Graph databases:
- are optional
- are projections
- are never the source of truth

Any Neo4j integration MUST:
- be derived from Postgres
- be disposable
- not introduce new semantics

---

### 8.2 Domain extensions

New domains (medical, industrial, academic) must:
- reuse core primitives
- not introduce domain-specific hacks
- express complexity via assertions, not schema forks

---

## 9. Code review checklist

Before approving a PR:

- [ ] Does this code preserve assertion immutability?
- [ ] Is any synthesis accidentally persisted?
- [ ] Is all logic explainable?
- [ ] Is uncertainty preserved end-to-end?
- [ ] Could this logic hallucinate meaning?

If any answer is “yes”, the PR must be revised.

---

## 10. Guiding principle (code-level)

> **The code must make epistemic shortcuts impossible.  
> If the system can lie silently, the architecture is wrong.**

This principle overrides all others.

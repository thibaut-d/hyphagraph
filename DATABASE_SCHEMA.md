# Logical data model (hypergraph-based)

This document describes the **logical database schema**.
It is **implementation-agnostic** (no SQL) and focuses on structure and meaning.

The schema models a **hypergraph of document-based assertions**.

---

## 1. Document

Represents a source of evidence.
No assertion may exist without a document.

| Field | Type | Description |
|------|------|-------------|
| id | UUID | Primary identifier |
| type | enum | study, guideline, notice, report, review, etc. |
| title | text | Document title |
| authors | text[] | List of authors |
| year | int | Publication year |
| source | text | Journal, agency, publisher |
| url | text | External reference |
| trust_level | float | Prior trust (e.g. guideline > study) |
| metadata | json | Optional structured metadata |

---

## 2. Concept

Represents a stable domain entity.
Concepts carry **no truth or causality**.

| Field | Type | Description |
|------|------|-------------|
| id | UUID | Primary identifier |
| type | enum | drug, disease, symptom, outcome, population, method, etc. |
| label | text | Canonical name |
| synonyms | text[] | Alternative labels |
| ontology_ref | text | Optional external ontology ID |

---

## 3. Assertion

Represents a **single claim made by one document**.
This is the hyper-edge.

| Field | Type | Description |
|------|------|-------------|
| id | UUID | Primary identifier |
| document_id | UUID | Source document |
| assertion_type | enum | effect, mechanism, risk, indication, observation |
| direction | enum | positive, negative, null, mixed |
| effect_size | json | Optional structured magnitude |
| local_confidence | float | Confidence derived from document quality |
| notes | text | Factual notes only |
| created_at | timestamp | Creation time |

Assertions are **immutable in meaning**.

---

## 4. AssertionConcept (hypergraph incidence)

Links an assertion to multiple concepts with explicit roles.
This table materializes the hypergraph.

| Field | Type | Description |
|------|------|-------------|
| assertion_id | UUID | Linked assertion |
| concept_id | UUID | Linked concept |
| role | enum | intervention, condition, outcome, population, methodology, exclusion |

Roles are **mandatory** and remove semantic ambiguity.

---

## 5. DerivedClaim (computed, optional)

Cached result of aggregation.
Never authored by humans.

| Field | Type | Description |
|------|------|-------------|
| id | UUID | Primary identifier |
| scope_hash | text | Hash of concepts + roles defining scope |
| score | float | Aggregated evidence score |
| uncertainty | float | Uncertainty / dispersion metric |
| computed_at | timestamp | Last computation time |

Derived claims can always be deleted and recomputed.

---

## 6. (Optional) AssertionExplanation

Stores explainability artifacts for derived claims.

| Field | Type | Description |
|------|------|-------------|
| derived_claim_id | UUID | Related derived claim |
| assertion_id | UUID | Contributing assertion |
| weight | float | Contribution weight |
| explanation | text | Human-readable explanation |

This table enables full traceability.

---

## 7. Key invariants

- Every Assertion references **exactly one Document**
- Concepts are reusable and context-free
- Assertions never encode consensus
- Synthesis exists only as DerivedClaim
- Hypergraph semantics are explicit via roles

---

## 8. Mental model summary

- **Document** → source
- **Assertion** → what the document says
- **Concept** → what it talks about
- **AssertionConcept** → how it talks about it
- **DerivedClaim** → what the system computes

> Knowledge is not stored.  
> It is derived.

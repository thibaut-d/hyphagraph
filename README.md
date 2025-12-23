# hyphagraph

Hypergraph-based Evidence Knowledge System

## 1. Vision & scientific motivation

### 1.1 The core problem

Across medicine, AI research, engineering, and enterprise knowledge, we face the same structural issue:

- Knowledge is primarily stored as **documents** (papers, guidelines, reports).
- Usable knowledge is produced via **human-written syntheses** (recommendations, reviews, wiki pages).
- When evidence is complex or contradictory, syntheses become:
  - partial or biased,
  - slow to update,
  - hard to audit,
  - prone to authority or opinion conflicts.

Large Language Models amplify this problem:
- they are excellent at producing fluent syntheses,
- but structurally **over-confident**,
- and vulnerable to hallucinations when asked to merge multiple sources.

The fundamental mistake is the same everywhere:

> **We store syntheses instead of storing what the documents actually say.**

---

### 1.2 The paradigm shift

This project proposes a different approach:

> **Humans and AI do not write knowledge.**  
> **They model assertions derived from documents.**  
> **All syntheses are computed, not authored.**

Concretely:
- Every document (study, guideline, notice, report) produces one or more **assertions**.
- Assertions may contradict each other.
- The system never resolves contradictions by opinion.
- Instead, it derives **weighted conclusions** using explicit, auditable rules.

This turns knowledge into a **calculable object**.

---

## 2. Why hypergraphs are essential

### 2.1 Limits of binary graphs

Traditional knowledge graphs rely on binary relations:

```

Drug → Effect
Disease → Symptom

````

Scientific conclusions are never binary. A real conclusion always depends on multiple dimensions:

- intervention
- population
- condition
- methodology
- outcome
- magnitude
- uncertainty

Encoding this in binary graphs leads to:
- loss of context,
- edge proliferation,
- implicit assumptions,
- fragile or misleading syntheses.

---

### 2.2 Hypergraph model

A **hypergraph** allows a single relation (hyper-edge) to connect **multiple nodes simultaneously**.

In this system:

> **One hyper-edge = one scientific assertion.**

A hyper-edge captures *all* elements required to preserve the meaning of a conclusion.

This is the key enabler for:
- explicit context,
- coexistence of contradictions,
- safe aggregation,
- traceability to sources.

---

## 3. Core data model

### 3.1 Document

A document is the only legitimate source of assertions.

```text
Document
- id
- type            # study, guideline, notice, report, etc.
- title
- authors
- year
- source          # journal, agency, publisher
- trust_level     # prior trust (e.g. guideline > single study)
- metadata        # free structured metadata
````

No assertion can exist without a document.

---

### 3.2 Concept

Concepts are stable entities of the domain. They do not carry truth.

```text
Concept
- id
- type        # drug, disease, symptom, outcome, population, method...
- label
- synonyms
- ontology_ref (optional)
```

---

### 3.3 Assertion (hyper-edge)

The central object of the system.

```text
Assertion
- id
- document_id
- assertion_type     # effect, mechanism, risk, indication...
- direction          # positive, negative, null, mixed
- effect_size        # optional structured value
- local_confidence   # derived from document quality
- notes              # factual notes only
```

Assertions never represent consensus. They represent *what one document states*.

---

### 3.4 AssertionConcept (hypergraph incidence)

This table materializes the hypergraph.

```text
AssertionConcept
- assertion_id
- concept_id
- role
```

Typical roles:

* intervention
* condition
* outcome
* population
* methodology
* exclusion

Roles are mandatory and remove semantic ambiguity.

---

### 3.5 DerivedClaim (computed, optional)

A derived claim is a cached result of aggregation.

```text
DerivedClaim
- id
- scope_hash
- score
- uncertainty
- last_computed_at
```

Derived claims:

* are never edited by humans,
* can be deleted and recomputed at any time,
* exist purely for performance and UX.

---

## 4. Worked example: Plaquenil & inflammation

### 4.1 Study A

* Population: Polyarthrite rhumatoïde
* Methodology: Randomized double-blind placebo-controlled trial
* Cohort: 200 patients
* Result: ≥30% inflammation reduction in 80% of patients

This produces one assertion hyper-edge:

* intervention: Plaquenil
* condition: Polyarthrite rhumatoïde
* outcome: Inflammation ↓
* methodology: RCT

---

### 4.2 Study B

* Population: Fibromyalgia
* Methodology: Placebo-controlled
* Cohort: 40 patients
* Result: improvement in 10%, no response in others

This produces a *different* assertion hyper-edge:

* intervention: Plaquenil
* condition: Fibromyalgia
* outcome: Inflammation ↓

No contradiction exists. These are distinct contextual facts.

---

### 4.3 Derived synthesis (example)

Computed view:

* Plaquenil → inflammation ↓

  * Polyarthrite rhumatoïde: strong evidence
  * Fibromyalgia: heterogeneous / weak evidence

The synthesis is:

* explainable,
* reversible,
* source-linked.

---

## 5. Role of AI in the system

AI is deliberately constrained.

### 5.1 What AI is allowed to do

* read a document
* extract factual conclusions
* map them into structured assertions
* optionally rephrase computed results for readability

### 5.2 What AI is not allowed to do

* invent assertions
* merge documents directly
* decide consensus
* override scoring rules

This structural constraint dramatically reduces hallucinations.

---

## 6. Technical stack (initial)

### Backend

* FastAPI
* PostgreSQL

PostgreSQL is used as the **source of truth hypergraph**, leveraging:

* relational integrity,
* transactional safety,
* auditability,
* analytical joins.

---

### Frontend

* React

The UI supports:

* document ingestion
* assertion editing / review
* computed synthesis visualization
* explanation and traceability

---

### LLM integration

A pluggable API layer supports multiple LLM providers:

* ChatGPT
* Gemini
* Mistral AI

LLMs are used exclusively for:

* extraction
* formatting
* explanation

Never as authoritative reasoning engines.

---

### Future extensions

* Neo4j (or equivalent) for graph algorithms and exploration
* DuckDB / Parquet for large-scale analytical aggregation
* Rule-learning and confidence calibration

---

## 7. Why this is more than a knowledge graph

This system is not a wiki.
It is not a traditional knowledge graph.

It is:

> **A system where knowledge is derived from weighted assertions, not written opinions.**

This enables:

* explicit contradiction handling
* reproducible syntheses
* safer AI usage
* reduced energy consumption
* domain-independent applicability

---

## 8. Scope

This repository is a **proof of concept**.

The goal is to demonstrate:

* feasibility,
* scientific soundness,
* architectural advantages.

Not to deliver medical recommendations.

---

## 9. Summary

* Assertions replace authored syntheses
* Hypergraphs preserve full context
* AI is constrained, not empowered
* Knowledge becomes computable


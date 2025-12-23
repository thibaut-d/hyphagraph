# HyphaGraph

**Hypergraph-based Evidence Knowledge System**

HyphaGraph is a research-oriented system designed to transform
document-based knowledge into a **computable, auditable, and explainable
knowledge graph**.

It is built around a simple idea:

> **Knowledge should not be written.  
> It should be derived from documented statements.**

---

## 1. Vision & scientific motivation

### 1.1 The core problem

Across medicine, AI research, engineering, and enterprise knowledge,
we face the same structural limitations:

- Knowledge primarily exists as **documents**  
  (papers, guidelines, reports, notices).
- Usable knowledge is produced as **human-written syntheses**  
  (reviews, recommendations, wiki pages).
- When evidence is complex or contradictory, syntheses become:
  - subjective or biased,
  - slow to update,
  - hard to audit,
  - difficult to trace back to sources.

Large Language Models amplify this issue:
- they generate fluent summaries,
- but are structurally **over-confident**,
- and prone to hallucinations when merging sources directly.

The underlying mistake is always the same:

> **We store conclusions instead of storing what documents actually say.**

---

### 1.2 The paradigm shift

HyphaGraph proposes a different model:

> **Humans and AI do not write knowledge.**  
> **They model document-grounded statements.**  
> **All syntheses are computed, not authored.**

Concretely:
- Documents are treated as **sources**, not knowledge.
- Each document produces one or more **claims**.
- Claims may contradict each other.
- Contradictions are preserved, not resolved by opinion.
- The system derives **weighted, explainable syntheses** using explicit rules.

Knowledge becomes a **computable object**, not a narrative artifact.

---

## 2. Why hypergraphs are essential

### 2.1 Limits of binary graphs

Most knowledge graphs rely on binary relations:

```

Drug → Effect
Disease → Symptom

```

Scientific and technical conclusions are never binary.
They always depend on multiple dimensions, such as:
- intervention,
- condition,
- population,
- methodology,
- outcome,
- magnitude,
- uncertainty.

Encoding this complexity in binary graphs leads to:
- loss of context,
- edge explosion,
- implicit assumptions,
- fragile or misleading conclusions.

---

### 2.2 Hypergraph approach

A **hypergraph** allows a single relation to connect **multiple entities at once**.

In HyphaGraph:

> **One hyper-edge represents one document-grounded claim.**

This preserves:
- full context,
- explicit roles,
- coexistence of contradictions,
- traceability to sources.

Hypergraphs are the minimal structure required to model real-world evidence
without distortion.

---

## 3. Conceptual architecture

HyphaGraph is structured around a clear separation of concerns:

- **Sources**  
  Documents that state something (studies, guidelines, reports).
- **Entities**  
  Stable domain objects (drugs, diseases, symptoms, populations, methods).
- **Relations (claims)**  
  What a source states about entities, in a given context.
- **Inference**  
  What the system computes from multiple claims.

> The database stores *statements*, not *beliefs*.

The full logical schema is defined in  
`DATABASE_SCHEMA.md`.

---

## 4. Role of AI in the system

AI is deliberately **constrained**.

### 4.1 What AI is allowed to do

- Read documents.
- Extract explicit, factual statements.
- Map statements into structured claims.
- Rephrase computed results for human readability.
- Generate explanations from traceable evidence.

### 4.2 What AI is not allowed to do

- Invent claims.
- Merge documents directly.
- Decide consensus.
- Override scoring or inference rules.
- Act as an authority.

This constraint is a design choice to:
- reduce hallucinations,
- preserve auditability,
- keep humans in control of interpretation.

---

## 5. Technical overview

### Backend

- **PostgreSQL**  
  Used as the source-of-truth hypergraph store:
  - transactional safety,
  - strong consistency,
  - auditability,
  - efficient analytical queries.

- **FastAPI**  
  For APIs, ingestion pipelines, inference orchestration, and LLM integration.

---

### Reasoning layer

- **TypeDB (planned / optional)**  
  Used as a reasoning engine:
  - explicit roles,
  - n-ary relations,
  - logical inference rules,
  - contradiction detection.

PostgreSQL stores the facts.  
TypeDB reasons about their implications.

---

### Frontend

- **React**

The UI focuses on:
- document ingestion,
- claim review and correction,
- computed syntheses,
- explanations and traceability.

---

### LLM integration

A pluggable LLM layer supports multiple providers (e.g. ChatGPT, Gemini, Mistral).

LLMs are used exclusively for:
- extraction,
- formatting,
- explanation.

Never as the source of truth.

---

## 6. Why this is not “just another knowledge graph”

HyphaGraph is not:
- a wiki,
- a recommendation engine,
- a traditional knowledge graph.

It is:

> **A system where knowledge is derived from weighted, document-grounded claims,
> rather than written opinions.**

This enables:
- explicit contradiction handling,
- reproducible syntheses,
- safer AI usage,
- strong explainability,
- domain-independent applicability.

---

## 7. Scope & disclaimer

This repository is a **proof of concept**.

Its goals are to demonstrate:
- conceptual soundness,
- architectural viability,
- advantages of hypergraph-based reasoning.

It is **not** intended to deliver medical, legal, or operational recommendations.

---

## 8. Summary

- Documents are sources, not knowledge.
- Claims are stored, not conclusions.
- Hypergraphs preserve full context.
- AI is constrained by design.
- Knowledge becomes computable.


# HyphaGraph

HyphaGraph is an experimental knowledge system based on hypergraphs, designed to transform documents into auditable, traceable, and computable knowledge instead of opaque summaries.

This repository is a proof of concept.


---

## What problem does it solve?

Most knowledge systems store information as documents or free-form summaries.
This makes knowledge:

- hard to audit,

- hard to update,

- hard to reason over,

- and prone to subjective interpretation.


HyphaGraph takes a different approach:
it extracts explicit factual statements (“claims”) from documents and represents them as a structured hypergraph, preserving sources, context, and contradictions.

### Typical use cases include:

- scientific literature analysis

- medical or technical knowledge curation

- comparison of contradictory sources

- explainable AI-assisted synthesis



---

## Project status

- ⚠️ Experimental / Proof of concept

- Not production-ready

- Data model and APIs are still evolving

- Intended for exploration, research, and prototyping



---

## Quick start

To get started with the project, read the following files in this order:

1. GETTING_STARTED.md
Setup instructions and local development workflow


2. ARCHITECTURE.md
Data model, hypergraph concepts, and system design


3. PROJECT.md
Scientific motivation, conceptual foundations, and detailed rationale




---

## Tech stack

- Backend: FastAPI, PostgreSQL

- Frontend: React

- LLM (optional): used in a constrained way for claim extraction and structuring
(not for generating conclusions)


---

## Contributing

Contributions are welcome.

Before contributing, please read the Markdown files containing essential documentation.

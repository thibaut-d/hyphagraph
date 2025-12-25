# Canonical Logical Data Model

This document defines the **canonical, implementation-agnostic data model** for a
**document-grounded knowledge hypergraph**.

> **Knowledge is not stored.  
> It is derived from documented relations.**

The model is designed to be:
- auditable and provenance-first
- efficiently storable in PostgreSQL
- isomorphic to TypeDB
- compatible with simplified graph projections
- safe and effective for LLM-based synthesis

---

## Core principles

- **Entities are context-free**
- **Relations carry meaning**
- **Roles remove ambiguity**
- **Sources provide provenance**
- **Inference is computed, never authored**

---

## Entity

Represents a **stable domain object**.

Entities never encode truth, causality, or interpretation.

```text
Entity
- id : UUID
- ui_category_id : UUID?
- label : text
- names : json?
- summary : json?
```

### Example

```json
{
  "id": "e1",
  "ui_category_id": "e_drug",
  "label": "paracetamol",
  "names": {
    "en": ["Paracetamol", "Acetaminophen"],
    "fr": ["Paracétamol"]
  },
  "summary": {
    "en": "Analgesic and antipyretic drug",
    "fr": "Médicament antalgique et antipyrétique"
  }
}
```

---

## Source

Represents a documentary source from which relations originate.

```text
Source
- id : UUID
- kind : text             # study, review, guideline, case_report…
- title : text
- authors : text[]?
- year : int?
- origin : text?          # journal, organization, publisher
- url : text
- trust_level : float?
- summary : json?         #i18n
- metadata : json?
```

### Invariants

- Every Relation MUST reference exactly one Source

- No relation exists without provenance

- Metadata is for document-level information only


### Example

```json
{
  "id": "s1",
  "kind": "study",
  "title": "Efficacy of Paracetamol for Chronic Pain",
  "authors": ["Doe J.", "Smith A."],
  "year": 2022,
  "origin": "Journal of Pain Research",
  "url": "https://example.org/study",
  "trust_level": 0.8
}
```

---

## Relation (Hyper-edge)

Represents a single claim made by a source.

```text
Relation
- id : UUID
- kind : text?           # effect, mechanism, association…
- direction : text?      # supports, contradicts, uncertain
- confidence : float?    # strength of assertion by the source
- scope : json?          # optional contextual qualifiers
- notes : json?          # i18n
- created_at : timestamp
```

### Semantics

- A relation expresses what a source claims

- It does NOT represent consensus or truth

- Confidence reflects source assertion strength, not system belief


### Example

```json
{
  "id": "r1",
  "kind": "effect",
  "direction": "supports",
  "confidence": 0.7,
  "scope": {
    "population": "adults",
    "condition": "chronic use"
  },
  "notes": "Moderate pain reduction observed"
}
```

---

## Role

Defines how entities participate in a relation.

```text
Role
- relation_id : UUID
- entity_id : UUID
- role_type : text
```

### Semantics

- Roles are mandatory

- A relation may involve any number of entities

- Role types carry the full semantic meaning


### Example

```json
[
  {
    "relation_id": "r1",
    "entity_id": "e1",
    "role_type": "agent"
  },
  {
    "relation_id": "r1",
    "entity_id": "e2",
    "role_type": "outcome"
  }
]
```

Where e2 might be an entity:

```json
{
  "id": "e2",
  "kind": "symptom",
  "label": "chronic pain"
}
```

---

## Attribute

Represents typed values attached to entities or relations.

```text
Attribute
- id : UUID
- owner_type : enum (entity, relation)
- owner_id : UUID
- key : text
- value : typed (string | number | boolean | json)
```

### Rules

- Attributes MUST NOT encode multi-entity claims or causality

- They are descriptive or qualifying only


### Example

```json
{
  "owner_type": "entity",
  "owner_id": "e1",
  "key": "atc_code",
  "value": "N02BE01"
}
```

---

### Inference (Computed)

Represents a computed synthesis or interpretation.

```text
Inference
- id : UUID
- scope_hash : text
- result : json
- uncertainty : float
- computed_at : timestamp
```

### Semantics

- Never authored by humans

- Fully disposable and recomputable

- Does NOT represent ground truth


### Example

```json
{
  "id": "i1",
  "scope_hash": "drug:e1|symptom:e2",
  "result": {
    "summary": {
      "en": "Evidence for pain reduction is mixed, with modest benefit in adults."
    }
  },
  "uncertainty": 0.4
}
```
---

## UI Categories

Used for display and navigation between Entities, not for semantic inference. Each site can have it's own UI catégories.

```text
UiCategory
- id : UUID
- slug : text
- labels : json             # i18n
- description : json?       # i18n
- order : int
```

### Semantics

- The slugs is lower case with no special characters.

- No sources for UI Categories. It is just a few basic wide categories designed to help user find what they are seeking. 

- Examples : Drugs, Biological Mechanisms, Diseases, Effects...


### Examples 

```json
{
  "id": "c1",
  "slug": "drug",
  "labels": {
    "en": "Drugs",
    "fr": "Médicaments"
  },
  "order": 10,
}
```


---

## Key invariants (Summary)

- Every Relation references exactly one Source

- Every Relation has at least one Role

- Entities are context-free and reusable

- No consensus is stored as fact

- All knowledge is derived from relations



---

## Mental model

- Entity → what exists

- Source → who says something

- Relation → what is said

- Role → how entities are involved

- Inference → what the system computes



---

## TypeDB alignment

Logical concept	TypeDB concept

- Entity	→ entity
- Source →	entity
- Relation → 	relation
- Role	 → relates
- Attribute	 → attribute
- Inference → 	query / rule result


This schema guarantees a lossless projection from PostgreSQL to TypeDB and supports auditable, explainable knowledge synthesis.

---

## Users

### Users schema 

We use FastAPI Users extension.

```
User
- id : UUID
- email : text (unique, indexed)
- hashed_password : text
- is_active : bool
- is_verified : bool
- is_superuser : bool
- created_at : timestamp
```

For now we rely on JWT only.

### User profile 

```
UserProfile
- user_id: UUID
- display_name: text
- avatar_url: text?
- locale: text?
- bio: json?         # i18n
```

### OAuth (not MVP)

We plan to support OAuth at some point of time.

```
OAuthAccount
- id
- user_id           # our internal user
- provider          # google | github | orcid
- external_id       # stable ID from provider
- created_at
```






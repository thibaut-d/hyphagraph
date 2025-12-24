# Schema

This document describes the **canonical logical data model** of the system.

The model represents a **document-grounded knowledge graph** expressed as a
**hypergraph of relations with explicit roles**.

It is designed to be:
- implementation-agnostic
- efficiently storable in **PostgreSQL**
- projectable to **TypeDB**
- compatible with simplified projections (e.g. Neo4j)
- friendly to LLM-based synthesis

> Knowledge is not stored.  
> It is derived from documented relations.

---

## Core principles

- **Entities are context-free**
- **Relations carry meaning**
- **Roles remove ambiguity**
- **Sources provide provenance**
- **Inference is computed, never authored**

---

## 1. Entity

Represents a **stable domain object**.

Entities do not encode truth, causality, or interpretation.

```text
Entity
- id : UUID
- kind : text
- label : text
- synonyms : text[]
````

### Notes

* Entities are reusable across all relations
* Multiple relations may reference the same entity
* Entities are the anchor points for queries

---

## 2. Source

Represents a **documentary source** from which relations originate.

```text
Source
- id : UUID
- kind : text
- title : text
- authors : text[]
- year : int
- origin : text
- url : text
- trust_level : float
- metadata : json?
```

### Invariants

* Every relation MUST reference exactly one source
* No relation exists without provenance

---

## 3. Relation

Represents a **single statement made by a source**.

A relation is the **hyper-edge** of the graph.

```text
Relation
- id : UUID
- kind : text
- direction : text
- confidence : float
- notes : text
- created_at : timestamp
```

### Semantics

* A relation expresses *what a source claims*
* Relations are atomic and immutable in meaning
* Relations do NOT represent consensus or truth

---

## 4. Role

Defines **how entities participate in a relation**.

```text
Role
- relation_id : UUID
- entity_id : UUID
- role_type : text
```

### Semantics

* Roles are mandatory
* A relation may involve any number of entities
* Role types carry the full semantic meaning

> In TypeDB, roles are native and this table disappears.

---

## 5. Attribute

Represents **typed values attached to entities or relations**.

```text
Attribute
- id : UUID
- owner_type : enum (entity, relation)
- owner_id : UUID
- key : text
- value : typed (string | number | boolean | json)
```

Attributes can store multilingual descriptions in JSON :

```json
{
  "de": "Description in German",
  "en": "Description in English",
  "fr": "Description in French"
}
```

### Notes

* Mirrors TypeDB `attribute`
* Optional if fixed columns are preferred
* Useful for extensibility without schema churn

---

## 6. Inference (computed)

Represents a **computed interpretation or synthesis**.

```text
Inference
- id : UUID
- scope_hash : text
- result : json
- uncertainty : float
- computed_at : timestamp
```

### Semantics

* Inferences are never authored by humans
* They can always be deleted and recomputed
* They do not represent ground truth

---

## 7. Explanation (optional)

Provides **traceability and explainability** for inferences.

```text
Explanation
- inference_id : UUID
- relation_id : UUID
- weight : float
- explanation : text
```

---

## 8. Key invariants

* Every Relation references exactly one Source
* Every Relation has at least one Role
* Entities are context-free and reusable
* No consensus is stored as a fact
* All knowledge is derived from relations

---

## 9. Mental model summary

* **Entity** → what exists
* **Source** → who says something
* **Relation** → what is said
* **Role** → how entities are involved
* **Inference** → what the system computes

---

## 10. TypeDB alignment

This schema is **isomorphic to TypeDB**:

| Logical concept | TypeDB concept      |
| --------------- | ------------------- |
| Entity          | entity              |
| Source          | entity              |
| Relation        | relation            |
| Role            | relates             |
| Attribute       | attribute           |
| Inference       | query / rule result |

This guarantees a **lossless projection** from PostgreSQL to TypeDB for deeper analysis.




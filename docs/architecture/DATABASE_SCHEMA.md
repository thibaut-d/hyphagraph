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
- created_at : timestamp
```

```text
EntityRevision
- id : UUID
- entity_id : UUID
- ui_category_id : UUID?
- slug : text
- summary : json?             # i18n 
- created_with_llm : text?    # LLM name
- created_by_user_id : UUID?
- created_at : timestamp
- is_current : bool
```

### Example

```json
{
  "id": "er1",
  "entity_id": "e1",
  "ui_category_id": "e_drug",
  "slug": "paracetamol",
  "summary": {
    "en": "Analgesic and antipyretic drug",
    "fr": "Médicament antalgique et antipyrétique"
  },
  "created_with_llm": null,
  "created_by_user_id": "u1",
  "created_at": "2024-01-15T10:30:00Z",
  "is_current": true
}
```
---

## Terms and Alias

Represents the different names of entities that can displayed on the UI or searched in documents.

```text
EntityTerm
- id : UUID
- entity_id : UUID
- term : text
- language : text?          # fr/en/NULL (NULL = international)
- display_order : int?      # smallest = printed first (nullable)
```

---

## Source

Represents a documentary source from which relations originate.

```text
Source
- id : UUID
- created_at : timestamp
```

```text
SourceRevision
- id : UUID
- source_id : UUID
- kind : text             # study, review, guideline, case_report…
- title : text
- authors : text[]?
- year : int?
- origin : text?          # journal, organization, publisher
- url : text
- trust_level : float?
- summary : json?         # i18n
- metadata : json?
- created_with_llm : text?
- created_by_user_id : UUID?
- created_at : timestamp
- is_current : bool
```

### Invariants

- Every Relation MUST reference exactly one Source

- No relation exists without provenance

- Metadata is for document-level information only


### Example

```json
{
  "id": "rs1",
  "source_id": "s1",
  "kind": "study",
  "title": "Efficacy of Paracetamol for Chronic Pain",
  "authors": ["Doe J.", "Smith A."],
  "year": 2022,
  "origin": "Journal of Pain Research",
  "url": "https://example.org/study",
  "trust_level": 0.8,
  "summary": {
    "en": "A randomized controlled trial examining paracetamol efficacy"
  },
  "metadata": {
    "doi": "10.1234/jpr.2022.001",
    "pubmed_id": "12345678"
  },
  "created_with_llm": "gpt-4",
  "created_by_user_id": "u1",
  "created_at": "2024-01-15T10:30:00Z",
  "is_current": true
}
```

---

## Relation (Hyper-edge)

Represents a single claim made by a source.

```
Relation
- id : UUID
- source_id : UUID
- created_at : timestamp
```

```text
RelationRevision
- id : UUID
- relation_id : UUID
- kind : text?           # effect, mechanism, association…
- direction : text?      # supports, contradicts, uncertain
- confidence : float?    # strength of assertion by the source
- scope : json?          # optional contextual qualifiers
- notes : json?          # i18n
- created_with_llm : text?
- created_by_user_id : UUID?
- created_at : timestamp
- is_current : bool
```

### Semantics

- A relation expresses what a source claims

- It does NOT represent consensus or truth

- Confidence reflects source assertion strength, not system belief


### Example

```json
{
  "id": "rr1",
  "relation_id": "r1",
  "kind": "effect",
  "direction": "supports",
  "confidence": 0.7,
  "scope": {
    "population": "adults",
    "condition": "chronic use"
  },
  "notes": "Moderate pain reduction observed",
  ...
}
```


### Relation Role

Defines how entities participate in a relation.

```text
RelationRoleRevision
- relation_revision_id : UUID
- entity_id : UUID
- role_type : text
- weight : float?        # computed inference relations only
- coverage : float?      # computed inference relations only
```

### Semantics

- Roles are mandatory

- A relation may involve any number of entities

- Role types carry the full semantic meaning

### Revision Strategy

A change in a relation revision always produces a new atomic claim, even if only the phrasing or confidence changed.
Roles are duplicated to preserve the exact claim boundary.


- Roles are tied to specific relation revisions via `relation_revision_id`

- When a relation is revised, all roles are duplicated for the new revision, even if unchanged

- This creates a complete snapshot of the relation at each revision point

- Trade-off: Data duplication ensures complete auditability and simplifies querying (no need to reconstruct historical state from deltas)


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
- created_at : timestamp
- updated_at : timestamp?
```

### Rules

- Attributes MUST NOT encode multi-entity claims or causality

- They are descriptive or qualifying only

- Can store external identifiers (DOI, PubMed IDs, ATC codes), URLs, or other metadata

- Attributes are generally stable but can be corrected if external identifiers change or errors are discovered

- Unlike entities and relations, attributes are not versioned - updates replace the previous value with a timestamp


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

An inference is a relation but the source ID is system.

```text
Relation
- id : UUID
- source_id : UUID # of the source "system"
- created_at : timestamp
```

The source is the engine used for computation.

```text
Source
- id : UUID
- kind : "system"
- title : "HyphaGraph inference engine v0.0.1"
```

The details live in a separated table than revisions.

```text
ComputedRelation
- relation_id : UUID        # PK, FK → Relation.id
- scope_hash : text
- model_version : text
- uncertainty : float
- computed_at : timestamp
```

### Scope Hash Algorithm

The `scope_hash` provides a deterministic identifier for a specific inference query scope.

**Algorithm:**
1. Collect all entities and their roles from the query scope
2. Sort entities by UUID to ensure deterministic ordering
3. Create canonical representation: `"role1:entity_id1|role2:entity_id2|..."`
4. Compute: `SHA256(canonical_representation)`
5. Store as hex string

**Example:**
- Query scope: drug `e1` with symptom `e2`
- Canonical form: `"agent:e1|outcome:e2"` (alphabetically sorted by role)
- Hash: `SHA256("agent:e1|outcome:e2")`

This allows efficient lookup of cached inferences for identical query scopes.

We use the same table for roles but we make use of optional per rôle weight and coverage.

```text
RelationRoleRevision
- relation_revision_id : UUID
- entity_id : UUID
- role_type : text
- weight : float?        # computed relations only
- coverage : float?     # computed relations only
```


### Semantics

- Never authored by humans

- Fully disposable and recomputable

- Does NOT represent ground truth

- The summary is an LLM generated human readable synthesis 


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

Used for display and navigation between Entities, not for semantic inference. Each site can have its own UI categories.

```text
UiCategory
- id : UUID
- slug : text
- labels : json             # i18n
- description : json?       # i18n
- order : int
- created_at : timestamp
- updated_at : timestamp?
```

### Semantics

- The slug is lower case with no special characters.

- No sources for UI Categories. It is just a few basic wide categories designed to help users find what they are seeking.

- Examples: Drugs, Biological Mechanisms, Diseases, Effects...

- While UI categories are not expected to change frequently, timestamps allow tracking when categories are added or modified for UI evolution.


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

## Database Constraints

### Foreign Key Constraints

- `EntityRevision.entity_id` → `Entity.id`
- `EntityRevision.ui_category_id` → `UiCategory.id` (nullable)
- `EntityRevision.created_by_user_id` → `User.id` (nullable)
- `EntityTerm.entity_id` → `Entity.id`
- `SourceRevision.source_id` → `Source.id`
- `SourceRevision.created_by_user_id` → `User.id` (nullable)
- `RelationRevision.relation_id` → `Relation.id`
- `RelationRevision.created_by_user_id` → `User.id` (nullable)
- `Relation.source_id` → `Source.id` (NOT NULL - every relation must have a source)
- `RelationRoleRevision.relation_revision_id` → `RelationRevision.id`
- `RelationRoleRevision.entity_id` → `Entity.id`
- `ComputedRelation.relation_id` → `Relation.id`
- `Attribute.owner_id` → `Entity.id` OR `Relation.id` (depending on `owner_type`)
- `UserProfile.user_id` → `User.id`
- `OAuthAccount.user_id` → `User.id`

### Unique Constraints

- `Entity.id` (primary key)
- `EntityRevision.id` (primary key)
- `Source.id` (primary key)
- `SourceRevision.id` (primary key)
- `Relation.id` (primary key)
- `RelationRevision.id` (primary key)
- `UiCategory.id` (primary key)
- `UiCategory.slug` (unique - no duplicate category slugs)
- `User.email` (unique - one account per email)
- `EntityTerm(entity_id, term, language)` (composite unique - same term can't appear twice for same entity/language)
- Only one `is_current = true` per `entity_id` in `EntityRevision`
- Only one `is_current = true` per `source_id` in `SourceRevision`
- Only one `is_current = true` per `relation_id` in `RelationRevision`

### Check Constraints

- `SourceRevision.trust_level` ∈ [0, 1] (if not null)
- `RelationRevision.confidence` ∈ [0, 1] (if not null)
- `ComputedRelation.uncertainty` ∈ [0, 1]
- `RelationRoleRevision.weight` ∈ [-1, 1] (if not null)
- `RelationRoleRevision.coverage` >= 0 (if not null)
- `UiCategory.order` >= 0
- `EntityTerm.display_order` >= 0 (if not null)
- `Attribute.owner_type` ∈ {'entity', 'relation'}

### Indexed Fields (Performance)

- `EntityRevision.entity_id` + `is_current` (for fetching current revision)
- `SourceRevision.source_id` + `is_current` (for fetching current revision)
- `RelationRevision.relation_id` + `is_current` (for fetching current revision)
- `Relation.source_id` (for finding all relations from a source)
- `RelationRoleRevision.entity_id` (for finding all relations involving an entity)
- `RelationRoleRevision.relation_revision_id` (for fetching roles)
- `ComputedRelation.scope_hash` (for lookup of cached inferences)
- `EntityTerm.term` (for search/autocomplete)
- `User.email` (for authentication)

---

## Key Invariants (Summary)

- Every Relation references exactly one Source

- Every Relation has at least one Role

- Entities are context-free and reusable

- No consensus is stored as fact

- All knowledge is derived from relations

- Each entity/source/relation has exactly one current revision (`is_current = true`)

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

We use a **custom JWT-based authentication system** instead of third-party frameworks.

**Design rationale:**
- FastAPI Users is in maintenance mode (no active development)
- Authentication is security-critical and must be fully transparent
- We prefer explicit, auditable code over framework magic
- See `ARCHITECTURE.md` Section 6 for authentication architecture

```
User
- id : UUID
- email : text (unique, indexed)
- hashed_password : text
- is_active : bool
- is_superuser : bool
- created_at : timestamp
```

**Authentication:**
- OAuth2 password flow with JWT access tokens
- Password hashing with bcrypt (passlib)
- Token signing with python-jose
- 30-minute token expiration (configurable)

**Authorization:**
- Explicit permission functions (no RBAC frameworks)
- Owner-based permissions with superuser override
- See `app/utils/permissions.py` for all permission checks

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

We plan to support OAuth at some point in time.

```text
OAuthAccount
- id : UUID
- user_id : UUID                    # FK → User.id
- provider : text                   # google | github | orcid
- external_id : text                # stable ID from provider
- access_token : text?              # encrypted
- refresh_token : text?             # encrypted
- token_expires_at : timestamp?
- created_at : timestamp
- updated_at : timestamp?
```

### Constraints

- Unique constraint on `(provider, external_id)` - one external account maps to one HyphaGraph user
- A user can have multiple OAuth providers linked






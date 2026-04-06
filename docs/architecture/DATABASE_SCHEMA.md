# Canonical Logical Data Model

This document defines the logical model and invariants that matter for implementation decisions.

It is intentionally concise. Use models, schemas, and migrations for executable detail.

## Core principles

- entities are context-free
- relations carry meaning
- roles remove ambiguity
- sources provide provenance
- inference is computed, never authored

## Core records

### Entity

Stable domain object with minimal immutable identity.

Current human-facing state lives in `EntityRevision`.

Key fields:

- `Entity`: `id`, `created_at`
- `EntityRevision`: `entity_id`, `ui_category_id`, `slug`, `summary`, `created_with_llm`, `created_by_user_id`, `created_at`, `is_current`

### EntityTerm

Search and display terms for an entity.

Key fields:

- `entity_id`, `term`, `language`, `display_order`, `is_display_name`

### Source

Documentary source from which claims originate.

Current source metadata lives in `SourceRevision`.

Key fields:

- `Source`: `id`, `created_at`
- `SourceRevision`: `source_id`, `kind`, `title`, `authors`, `year`, `origin`, `url`, `trust_level`, `summary`, `metadata`, `created_with_llm`, `created_by_user_id`, `created_at`, `is_current`

### Relation

A single claim made by one source.

Current claim state lives in `RelationRevision`.

Key fields:

- `Relation`: `id`, `source_id`, `created_at`
- `RelationRevision`: `relation_id`, `kind`, `direction`, `confidence`, `scope`, `notes`, `created_with_llm`, `created_by_user_id`, `created_at`, `is_current`

### RelationRoleRevision

Defines how entities participate in a relation revision.

Key fields:

- `relation_revision_id`, `entity_id`, `role_type`, `weight`, `coverage`

### ComputedRelation

Cached, disposable, recomputable inference output.

Key fields:

- `relation_id`, `scope_hash`, `model_version`, `uncertainty`, `computed_at`

### UiCategory

Display-oriented grouping for entities.

Key fields:

- `slug`, `labels`, `description`, `order`

### User

Authentication and provenance actor.

Key fields:

- `id`, `email`, `hashed_password`, `is_active`, `is_superuser`, `created_at`

## Revision model

Mutable domain objects use a base-table plus revision-table pattern.

Rules:

- base tables hold stable identity
- revision tables hold mutable state
- only one revision is current for a given base record
- historical revisions remain queryable
- provenance is preserved with `created_by_user_id` when available
- user deletion should not destroy historical provenance records

## Provenance rules

- every relation references exactly one source
- no claim exists without provenance
- created-with-LLM metadata is descriptive, not authoritative
- computed outputs never replace source-grounded claims

## Relation semantics

- a relation stores what a source claims, not what the system believes
- confidence reflects source assertion strength, not system truth
- roles are mandatory because relations carry meaning through role assignment
- revising a relation creates a new full claim snapshot, including roles

## Inference rules

- inference is derived from stored relations
- computed outputs are disposable and recomputable
- no consensus is stored as authoritative fact
- uncertainty must remain explicit

## Scope hash

`ComputedRelation.scope_hash` is the deterministic identifier for an inference query scope.

Requirements:

1. build a canonical representation of the scoped entities and roles
2. sort deterministically before hashing
3. hash the canonical form
4. use the result for cache lookup of equivalent scopes

The exact implementation may evolve, but determinism for identical scopes is required.

## Important constraints

- `Relation.source_id` is required
- only one current revision is allowed per base record
- revision provenance foreign keys should use `SET NULL` on user delete
- `trust_level`, `confidence`, and `uncertainty` are bounded numeric values
- category slugs and user emails are unique
- entity terms are unique per entity, term, and language

## Design guardrails

- do not store human-authored synthesis as fact
- do not let LLM output become authoritative
- do not encode multi-entity claims as simple attributes
- do not bypass revision history for mutable records

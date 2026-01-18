# Inference Model Analysis - Gap Between Spec and Implementation

**Date**: 2026-01-14
**Issue**: Computed Inference shows same score for all entities of same relation type

---

## Problem Statement

**User Observation**:
> "Dans le rôle Treats de Fibromyalgia, tous les traitements ont le même score et coverage.
> C'est impossible - duloxetine et pregabalin ne peuvent pas avoir exactement le même score."

**Current Display**:
```
treats
  Score: 1.00
  Coverage: 29.0
  Connected to: duloxetine, pregabalin, aerobic-exercise, ...
  (All 29 entities share the same aggregated score)
```

**Expected Display** (per spec):
```
Treatments for Fibromyalgia:
  - duloxetine: score 0.85, coverage 3.2, confidence 78%
  - pregabalin: score 0.72, coverage 2.1, confidence 65%
  - aerobic-exercise: score 0.91, coverage 1.0, confidence 52%
```

---

## Root Cause Analysis

### What COMPUTED_RELATIONS.md Specifies

**Section 6-7**: Compute inference **per (Entity, Role) pair**

```
s_hat(E, r) = score for entity E in role r
```

**Example from spec**:
- (Fibromyalgia, "treatment") → Which entities treat fibromyalgia
- Calculate separately for EACH treatment entity
- duloxetine: score based on duloxetine→treats→fibromyalgia relations
- pregabalin: score based on pregabalin→treats→fibromyalgia relations

### What Current Implementation Does

**InferenceService._compute_role_inferences()**:
```python
# Current (incorrect):
for relation_type in relation_types:  # treats, biomarker_for, etc.
    # Aggregates ALL relations of this type together
    # Returns ONE score for ALL 29 treatments combined
```

**Issue**: Aggregates by **relation TYPE**, not by **linked entity**.

---

## Architectural Gap

### Semantic Roles vs Grammatical Roles

**COMPUTED_RELATIONS.md assumes**:
- Semantic roles: "agent", "target", "mechanism", "population"
- Example: duloxetine (agent) treats fibromyalgia (target) in adults (population)

**HyphaGraph currently has**:
- Grammatical roles: "subject", "object"
- Example: duloxetine (subject) treats fibromyalgia (object)

**Missing**:
- Rôles sémantiques riches (agent, target, effect, population, condition)
- Hypergraph complet avec N entités par relation
- Actuellement : presque toutes les relations sont binaires (subject/object)

---

## Solution Options

### Option 1: Full Spec Implementation (Ideal but Complex)

**Requires**:
1. Add semantic role types (agent, target, effect, population, condition)
2. Allow N roles per relation (not just 2)
3. Compute inference per (entity, semantic_role) pair
4. Display grouped by semantic role

**Effort**: 3-5 jours (architectural change)

**Example**:
```
Fibromyalgia as Target (entities that target fibromyalgia):
  Pharmacological Agents:
    - duloxetine: score 0.85, 3 sources, confidence 78%
    - pregabalin: score 0.72, 2 sources, confidence 65%

  Exercise Interventions:
    - aerobic-exercise: score 0.91, 1 source, confidence 52%
```

---

### Option 2: Per-Entity Inference (Pragmatic Fix)

**Keep current model** (subject/object, relation types) but calculate **per linked entity**.

**Modified RoleInference**:
```typescript
interface EntityInference {
  entity_slug: string;
  score: number;
  coverage: number;
  confidence: number;
  disagreement: number;
  source_count: number;
}

interface RoleInference {
  role_type: string;  // "treats", "biomarker_for"
  entities: EntityInference[];  // One per linked entity
}
```

**Algorithm**:
```python
# For each relation type (treats, biomarker_for, etc.)
for relation_type in relation_types:

    # Group by linked entity
    entity_relations = defaultdict(list)

    for relation in relations:
        if relation.kind == relation_type:
            # Find the OTHER entity (not current entity)
            other_entities = [role for role in relation.roles
                            if role.entity_id != current_entity_id]

            for other in other_entities:
                entity_relations[other.entity_slug].append(relation)

    # Calculate score PER entity
    entity_inferences = []
    for entity_slug, rels in entity_relations.items():
        score = calculate_score(rels)
        coverage = sum(r.weight for r in rels)
        confidence = 1 - exp(-coverage / 3)

        entity_inferences.append(EntityInference(
            entity_slug=entity_slug,
            score=score,
            coverage=coverage,
            confidence=confidence,
            source_count=len(rels)
        ))
```

**Display**:
```
Treatments (treats relation, fibromyalgia as object):
  ┌─ duloxetine ────────────────────┐
  │ Score: 0.85 ████████░░          │
  │ 3 sources, Confidence: 78%      │
  │ [Explain]                       │
  └─────────────────────────────────┘

  ┌─ pregabalin ────────────────────┐
  │ Score: 0.72 ███████░░░          │
  │ 2 sources, Confidence: 65%      │
  │ [Explain]                       │
  └─────────────────────────────────┘
```

**Effort**: 1 jour (refactor existing code)

---

### Option 3: Simple List (Immediate Fix)

**Don't compute aggregated scores** - just show the individual relations.

Keep only "Source Evidence" section, remove misleading "Computed Inference".

**Display**:
```
Relationships

Treatments:
  • duloxetine treats fibromyalgia [supports] confidence: 0.80
    Source: Study A
  • duloxetine treats fibromyalgia [supports] confidence: 0.75
    Source: Study B
  • pregabalin treats fibromyalgia [supports] confidence: 0.70
    Source: Study C
```

**Effort**: 2 heures (hide Computed Inference, improve Source Evidence)

---

## Recommendation

**Short term (Now)**: Option 3 - Hide misleading Computed Inference
- Shows actual evidence without misleading aggregation
- Each relation visible with its own confidence
- User can see which sources support which treatments

**Medium term (Next sprint)**: Option 2 - Per-entity inference
- Calculate score per linked entity
- Show "duloxetine: 0.85" not "treats: 1.0"
- Keeps current architecture (subject/object)

**Long term (v2.0)**: Option 1 - Full semantic roles
- Implement hypergraph model as intended
- Semantic roles (agent, target, population, condition)
- True multi-entity relations

---

## Current State

**What works**:
- ✅ Source Evidence section (shows individual relations correctly)
- ✅ Each relation has its own confidence

**What's broken**:
- ❌ Computed Inference (aggregates incorrectly)
- ❌ Shows one score for 29 different treatments
- ❌ Misleading to users

**Immediate action**: Hide or fix Computed Inference section.

Which option do you prefer?
1. Hide Computed Inference (2 hours)
2. Per-entity scores (1 day)
3. Full semantic roles (3-5 days)

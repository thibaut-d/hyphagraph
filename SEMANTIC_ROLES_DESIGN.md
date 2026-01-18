# Semantic Roles Design - Hypergraph Model

**Date**: 2026-01-14
**Purpose**: Define semantic role types for true hypergraph relations

---

## 1. Semantic Role Types

### Core Roles (Clinical/Medical Domain)

| Role | Description | Example |
|------|-------------|---------|
| **agent** | Entity performing action/causing effect | duloxetine (in "duloxetine treats fibromyalgia") |
| **target** | Entity receiving action/being affected | fibromyalgia (in "duloxetine treats fibromyalgia") |
| **outcome** | Result or effect produced | pain-relief (in "duloxetine produces pain-relief") |
| **mechanism** | Biological mechanism involved | serotonin-reuptake (in "duloxetine works via serotonin-reuptake") |
| **population** | Patient population or demographic | adults, women, elderly |
| **condition** | Clinical condition or context | chronic-pain, depression |
| **dosage** | Dose or quantity | 60mg-daily |
| **duration** | Time period | 12-weeks |
| **route** | Administration route | oral, intravenous |

### Measurement/Study Roles

| Role | Description | Example |
|------|-------------|---------|
| **measured_by** | Assessment tool | VAS (in "pain measured_by VAS") |
| **biomarker** | Diagnostic/prognostic marker | crp (in "crp biomarker for inflammation") |
| **control_group** | Comparison group in study | healthy-controls, placebo |
| **study_group** | Experimental group | fibromyalgia-patients |

### Contextual Roles

| Role | Description | Example |
|------|-------------|---------|
| **location** | Anatomical location | brain, joints |
| **frequency** | How often | daily, weekly |
| **severity** | Intensity level | mild, moderate, severe |
| **effect_size** | Magnitude of effect | 25%-reduction |

---

## 2. Relation Type → Semantic Roles Mapping

### "treats" Relation
```
duloxetine treats fibromyalgia in adults at 60mg daily

Roles:
  - agent: duloxetine
  - target: fibromyalgia
  - population: adults
  - dosage: 60mg-daily
```

### "biomarker_for" Relation
```
miRNA-223-3p is biomarker for fibromyalgia in women

Roles:
  - biomarker: mirna-223-3p
  - target: fibromyalgia
  - population: women
```

### "causes" Relation
```
fibromyalgia causes sleep-disturbance

Roles:
  - agent: fibromyalgia
  - outcome: sleep-disturbance
```

### "mechanism" Relation
```
duloxetine works via serotonin-reuptake-inhibition

Roles:
  - agent: duloxetine
  - mechanism: serotonin-reuptake-inhibition
```

---

## 3. Inference Calculation Per Semantic Role

### Current (Wrong)
```
treats: score 1.0, coverage 29
  (aggregates all 29 treatments together)
```

### Correct (Per COMPUTED_RELATIONS.md)
```
For each entity E_other connected to Fibromyalgia via "agent" role in "treats" relations:

  s_hat(E_other, agent in treats) = weighted average of evidence

Example:
  duloxetine (as agent):
    - 3 relations where duloxetine treats fibromyalgia
    - weights: [0.8, 0.75, 0.9] (confidences)
    - score: (0.8 + 0.75 + 0.9) / 3 = 0.82
    - coverage: 3.0
    - confidence: 1 - exp(-3/3) = 63%

  pregabalin (as agent):
    - 2 relations where pregabalin treats fibromyalgia
    - weights: [0.7, 0.7]
    - score: 0.70
    - coverage: 2.0
    - confidence: 49%
```

---

## 4. Implementation Plan

### Phase 1: Database Schema (2-3 hours)

**Create semantic_role_types table**:
```sql
CREATE TABLE semantic_role_types (
  role_type VARCHAR(50) PRIMARY KEY,
  label JSONB,  -- {"en": "Agent", "fr": "Agent"}
  description TEXT,
  category VARCHAR(50),  -- core, measurement, contextual
  examples TEXT
);
```

**Seed initial roles** (16 semantic roles).

**Modify relation_role_revisions** (backward compatible):
- Keep existing role_type field
- For old data: "subject", "object" (grammatical)
- For new data: "agent", "target", "population", etc. (semantic)

### Phase 2: LLM Prompt Update (2-3 hours)

**Add roles to extraction prompt**:
```
For each relation, specify:
- relation_type: treats, causes, etc.
- roles: [
    {entity_slug: "duloxetine", role_type: "agent"},
    {entity_slug: "fibromyalgia", role_type: "target"},
    {entity_slug: "adults", role_type: "population"}
  ]
```

**Example output**:
```json
{
  "relation_type": "treats",
  "roles": [
    {"entity_slug": "duloxetine", "role_type": "agent"},
    {"entity_slug": "fibromyalgia", "role_type": "target"},
    {"entity_slug": "adults", "role_type": "population"},
    {"entity_slug": "60mg-daily", "role_type": "dosage"}
  ],
  "confidence": "high"
}
```

### Phase 3: Inference Calculation Rewrite (4-6 hours)

**New algorithm**:
```python
def compute_inferences_by_semantic_role(entity_id, relations):
    """
    Compute inference for (Entity, SemanticRole) pairs.

    For Fibromyalgia:
      - (Fibromyalgia, target) → entities that target it (treatments)
      - (Fibromyalgia, agent) → entities it causes (symptoms)
    """

    # Group by (semantic_role, other_entity)
    role_entity_relations = defaultdict(lambda: defaultdict(list))

    for rel in relations:
        for role in rel.roles:
            if role.entity_id != entity_id:
                # This is a linked entity
                semantic_role = role.role_type  # "agent", "target", etc.
                entity_slug = role.entity_slug

                role_entity_relations[semantic_role][entity_slug].append(rel)

    # Calculate per (role, entity) pair
    results = []

    for semantic_role, entities in role_entity_relations.items():
        entity_scores = []

        for entity_slug, rels in entities.items():
            score = aggregate_evidence(rels)
            coverage = sum(r.weight for r in rels)
            confidence = 1 - exp(-coverage / 3)

            entity_scores.append({
                'entity_slug': entity_slug,
                'score': score,
                'coverage': coverage,
                'confidence': confidence,
                'source_count': len(rels)
            })

        results.append({
            'semantic_role': semantic_role,
            'entities': entity_scores
        })

    return results
```

### Phase 4: UI Update (3-4 hours)

**New display**:
```tsx
<Typography variant="h5">Relationships</Typography>

{/* Group by semantic role */}
{inferences.map(roleGroup => (
  <Card>
    <CardHeader title={formatRole(roleGroup.semantic_role)} />
    <CardContent>
      {/* List entities with individual scores */}
      {roleGroup.entities.map(entity => (
        <Box>
          <Link to={`/entities/${entity.entity_slug}`}>
            {entity.entity_slug}
          </Link>
          <ScoreBar score={entity.score} />
          <Typography>
            {entity.source_count} sources, {entity.confidence}% confidence
          </Typography>
        </Box>
      ))}
    </CardContent>
  </Card>
))}
```

**Example output**:
```
Targeted By (entities that target fibromyalgia):
  ┌─ duloxetine ─────────────────────┐
  │ Score: 0.85 ████████░░           │
  │ 3 sources, 78% confidence        │
  └──────────────────────────────────┘

  ┌─ pregabalin ─────────────────────┐
  │ Score: 0.72 ███████░░░           │
  │ 2 sources, 65% confidence        │
  └──────────────────────────────────┘
```

---

## 5. Migration Strategy

### Backward Compatibility

**Keep old data working**:
- Existing relations with "subject"/"object" still work
- Map to semantic roles:
  - "subject" in "treats" → "agent"
  - "object" in "treats" → "target"
  - "subject" in "biomarker_for" → "biomarker"
  - "object" in "biomarker_for" → "target"

### Gradual Migration

**Phase 1**: New extractions use semantic roles
**Phase 2**: Background job migrates old relations
**Phase 3**: Deprecate subject/object

---

## 6. Validation

**Test with fibromyalgia**:
- 29 "treats" relations should become:
  - 29 entities with "agent" role
  - 1 entity (fibromyalgia) with "target" role
  - Each agent gets individual score

**Expected**:
```
Fibromyalgia as Treatment Target:
  - duloxetine (agent): score 0.85, 3 sources
  - pregabalin (agent): score 0.70, 2 sources
  - aerobic-exercise (agent): score 0.90, 1 source
  ... (29 total)
```

**Not**:
```
treats: score 1.0, 29 sources (all mixed together)
```

---

## Next Steps

1. Create semantic_role_types table
2. Seed 16 semantic roles
3. Update LLM prompts with role extraction
4. Rewrite inference calculation
5. Update UI display
6. Test with fibromyalgia (should see per-entity scores)

Estimated: 10-15 hours total for complete implementation.

# Computed Relations — Inference Model

This document describes how HyphaGraph computes **derived (computed) relations**
from source relations.

> Knowledge is not stored.  
> It is derived from documented relations.

All formulas below are expressed in **explicit ASCII math** for full GitHub compatibility.

---

## 1. Notation

- E : an entity of interest
- H(E) : set of source relations involving E
- r : a role type (effect, outcome, mechanism, etc.)

For each relation h in H(E):

- w_h >= 0 : global relation weight (source trust, study quality…)
- R(h) : set of roles exposed by relation h

---

## 2. Absence vs information

**Absence of a role is absence of information, not a zero value.**

If a role does not appear in a relation, it does not contribute to inference.

---

## 3. Claim-level model (inside a relation)

Each relation is decomposed into claims.

For each claim c:

- r(c) : role type
- p(c) ∈ { -1, 0, +1 } : polarity  
  +1 = supports  
  -1 = contradicts  
  0 = neutral / no effect
- i(c) ∈ (0, 1] : intensity (strength of the claim)

### Claim contribution

```
x(c) = p(c) × i(c)
```

x(c) ∈ [-1, 1]

---

## 4. Role contribution within a relation

For a relation h and role r:

```
x(h, r) =
  sum over claims c in h with role r of x(c)
  ------------------------------------------------
  sum over claims c in h with role r of |x(c)|
```

Properties:
- x(h, r) ∈ [-1, 1]
- Internal contradictions are normalized
- If no claim exists for role r, x(h, r) is undefined

---

## 5. Role exposure mask

```
m(h, r) = 1 if role r is exposed in relation h
m(h, r) = 0 otherwise
```

This guarantees that non-exposed roles never influence inference.

---

## 6. Evidence aggregation (per role)

### Weighted evidence

```
Ev(E, r) = sum over h in H(E) of:
           w_h × m(h, r) × x(h, r)
```

### Information coverage

```
Cov(E, r) = sum over h in H(E) of:
            w_h × m(h, r)
```

Coverage measures **how much information exists**, not how positive it is.

---

## 7. Normalized inference score

For each entity–role pair:

```
s_hat(E, r) =
  Ev(E, r) / Cov(E, r)    if Cov(E, r) > 0
  undefined               otherwise
```

Properties:
- s_hat(E, r) ∈ [-1, 1]
- Comparable across roles
- Stable under partial coverage
- Independent of relation count

---

## 8. Confidence and uncertainty

Confidence is derived from coverage:

```
confidence(E, r) = 1 - exp( -λ × Cov(E, r) )
```

Where λ > 0 controls saturation speed.

```
uncertainty(E, r) = 1 - confidence(E, r)
```

---

## 9. Disagreement (contradiction measure)

```
Dis(E, r) =
  1 - | sum_h w_h × m(h, r) × x(h, r) |
      ---------------------------------
      sum_h w_h × m(h, r) × |x(h, r)|
```

Interpretation:
- 0 → full agreement
- 1 → maximal contradiction

---

## 10. Computed relation construction

For a given inference scope:

1. Create a new Relation with a system source
2. Attach a ComputedRelation record
3. For each role r:
   - weight = s_hat(E, r)
   - coverage = Cov(E, r)
4. Record dependencies to source relations

---

## 11. What is stored vs derived

Stored:
- role weights
- coverage
- uncertainty
- provenance

Not stored:
- probabilities
- truth
- consensus
- opaque scores

---

## 12. Summary

A computed relation is a **hyper-edge whose roles carry normalized evidence
scores**, derived from documented relations, weighted by provenance,
and fully explainable.
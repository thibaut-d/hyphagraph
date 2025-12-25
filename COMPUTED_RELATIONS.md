# Computed Relations — Inference Model

This document describes **how HyphaGraph computes derived (computed) relations** from source relations.

> **Knowledge is not stored.  
> It is derived from documented relations.**

Computed relations are **materialized, disposable hyper-edges** whose roles carry **numerical weights** derived from auditable mathematical rules.

This document defines those rules.

---

## 1. Conceptual overview

- A **source relation** expresses what a document claims.
- A **computed relation** expresses what the system derives from multiple source relations.
- Computed relations:
  - are never authored by humans
  - are fully recomputable
  - never represent ground truth
  - are structurally identical to source relations

The only difference lies in **how role weights are computed**.

---

## 2. Notation

Let:

- \( E \) be an entity of interest.
- \( \mathcal{H}(E) \) be the set of source relations involving \( E \).
- \( r \in \mathcal{R} \) be a role type (e.g. effect, outcome, mechanism).
- Each relation \( h \in \mathcal{H}(E) \) has:
  - a global weight \( w_h \ge 0 \) (derived from source trust, study quality, etc.)
  - a set of exposed roles \( \mathcal{R}(h) \subseteq \mathcal{R} \)

---

## 3. Absence vs information

A core principle of HyphaGraph:

> **Absence of a role is absence of information — not a zero value.**

Therefore:
- If a role does not appear in a relation, it contributes nothing.
- Only explicitly exposed roles participate in inference.

---

## 4. Claim-level model (inside a relation)

Each source relation \( h \) is composed of **claims**.

For each claim \( c \):

- \( r(c) \): role type
- \( p(c) \in \{-1, 0, +1\} \): polarity  
  - +1: supports
  - −1: contradicts
  - 0: neutral / no effect
- \( i(c) \in (0, 1] \): intensity (strength of the claim)

### Claim contribution

\[
x(c) = p(c) \times i(c)
\quad\in [-1, 1]
\]

---

## 5. Role contribution within a relation

For a relation \( h \) and a role \( r \):

If \( h \) contains at least one claim for role \( r \):

\[
x_{h,r} =
\frac{
\sum\limits_{c \in h,\ r(c)=r} x(c)
}{
\sum\limits_{c \in h,\ r(c)=r} |x(c)|
}
\]

Properties:
- \( x_{h,r} \in [-1,1] \)
- Internal contradictions are naturally normalized
- If no claim exists for role \( r \), then \( x_{h,r} \) is **undefined**

---

## 6. Role exposure mask

We define a presence mask:

\[
m_{h,r} =
\begin{cases}
1 & \text{if } r \in \mathcal{R}(h) \\
0 & \text{otherwise}
\end{cases}
\]

This ensures that non-exposed roles never influence inference.

---

## 7. Evidence aggregation (per role)

### Weighted evidence

\[
\mathrm{Ev}(E,r) =
\sum_{h \in \mathcal{H}(E)}
w_h \cdot m_{h,r} \cdot x_{h,r}
\]

### Information coverage

\[
\mathrm{Cov}(E,r) =
\sum_{h \in \mathcal{H}(E)}
w_h \cdot m_{h,r}
\]

Coverage measures **how much information exists**, not how positive it is.

---

## 8. Normalized inference score

For each entity–role pair:

\[
\hat{s}(E,r) =
\begin{cases}
\dfrac{\mathrm{Ev}(E,r)}{\mathrm{Cov}(E,r)} & \text{if } \mathrm{Cov}(E,r) > 0 \\
\varnothing & \text{otherwise}
\end{cases}
\]

Properties:
- \( \hat{s}(E,r) \in [-1,1] \)
- Comparable across roles
- Independent of the number of relations
- Stable under partial coverage

---

## 9. Confidence / uncertainty

Confidence is derived from coverage, not polarity.

A bounded confidence function:

\[
c(E,r) = 1 - \exp(-\lambda \cdot \mathrm{Cov}(E,r))
\quad\in[0,1]
\]

Where \( \lambda > 0 \) controls saturation speed.

Uncertainty can be defined as:

\[
\mathrm{uncertainty}(E,r) = 1 - c(E,r)
\]

---

## 10. Disagreement (contradiction measure)

To explicitly capture conflicting evidence:

\[
\mathrm{Dis}(E,r) =
1 -
\frac{
\left| \sum\limits_h w_h m_{h,r} x_{h,r} \right|
}{
\sum\limits_h w_h m_{h,r} |x_{h,r}|
}
\]

Interpretation:
- 0 → all evidence agrees
- 1 → maximal contradiction

---

## 11. Computed relation construction

For a given inference scope:

1. A new `Relation` is created with a **system source**
2. A `ComputedRelation` record is attached
3. For each role \( r \):
   - a `RelationRoleRevision` is created
   - `weight = \hat{s}(E,r)`
   - `coverage = \mathrm{Cov}(E,r)`
4. Dependencies to source relations are recorded

---

## 12. What is (and is not) stored

Stored:
- role weights
- coverage
- uncertainty
- provenance

Not stored:
- probabilities
- consensus
- truth
- opaque embeddings

---

## 13. Design guarantees

This inference model guarantees:

- Auditability
- Determinism
- Absence ≠ zero
- Explicit contradiction
- Compatibility with PostgreSQL and TypeDB
- Safe LLM usage limited to text synthesis

---

## 14. Summary

> **A computed relation is a hyper-edge whose roles carry normalized evidence scores,  
derived from documented relations, weighted by provenance, and fully explainable.**

This model is the foundation for all higher-level synthesis in HyphaGraph.
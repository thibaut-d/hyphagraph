"""
Inference math primitives.

All functions are pure (no I/O, no side effects) and operate on normalised
numerical values in the range [-1, 1] for scores and [0, 1] for confidence /
disagreement. The aggregation model is documented in docs/architecture/COMPUTED_RELATIONS.md.
"""
import math
from typing import Optional


def compute_claim_score(polarity: int, intensity: float) -> float:
    """Return a signed score by multiplying polarity (+1/-1) with intensity (0-1)."""
    return polarity * intensity


def compute_role_contribution(claims: list[float]) -> Optional[float]:
    """
    Aggregate a list of signed claim scores into a single role contribution.

    Returns the ratio of signed sum to absolute sum, clamped to [-1, 1].
    Returns None if the claims list is empty.
    """
    if not claims:
        return None

    numerator = sum(claims)
    denominator = sum(abs(claim) for claim in claims)
    if denominator == 0:
        return 0

    contribution = numerator / denominator
    return max(-1.0, min(1.0, contribution))


def aggregate_evidence(relations_data: list[dict], role: str) -> dict:
    """
    Aggregate weighted evidence from multiple relations for a given role.

    Each entry in relations_data must have:
      - "weight": float (source confidence, defaults to 1.0)
      - "roles": dict mapping role_type → contribution (float)

    Returns a dict with:
      - "score": weighted mean contribution, or None if no evidence
      - "coverage": sum of weights for relations that have the role
    """
    evidence = 0.0
    coverage = 0.0

    for relation in relations_data:
        weight = relation.get("weight", 1.0)
        roles = relation.get("roles", {})
        if role not in roles:
            continue

        contribution = roles[role]
        if contribution is None:
            continue

        evidence += weight * contribution
        coverage += weight

    return {
        "score": evidence / coverage if coverage > 0 else None,
        "coverage": coverage,
    }


def compute_confidence(coverage: float, lambda_param: float = 1.0) -> float:
    """
    Convert evidence coverage into a [0, 1] confidence value.

    Uses an exponential saturation model: confidence = 1 - e^(-λ × coverage).
    Higher coverage → higher confidence; lambda controls the growth rate.
    Returns 0.0 for zero or negative coverage.
    """
    if coverage <= 0:
        return 0.0

    return 1 - math.exp(-lambda_param * coverage)


def compute_disagreement(relations_data: list[dict], role: str) -> float:
    """
    Measure how much sources disagree on a role's direction.

    Returns a value in [0, 1]:
      - 0.0 = complete agreement (all sources point the same way)
      - 1.0 = complete cancellation (equal positive and negative weight)

    Computed as 1 - |signed_sum| / absolute_sum.
    """
    signed_sum = 0.0
    absolute_sum = 0.0

    for relation in relations_data:
        weight = relation.get("weight", 1.0)
        roles = relation.get("roles", {})
        if role not in roles:
            continue

        contribution = roles[role]
        if contribution is None:
            continue

        signed_sum += weight * contribution
        absolute_sum += weight * abs(contribution)

    if absolute_sum == 0:
        return 0.0

    return 1 - (abs(signed_sum) / absolute_sum)

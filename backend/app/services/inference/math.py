import math
from typing import Optional


def compute_claim_score(polarity: int, intensity: float) -> float:
    return polarity * intensity


def compute_role_contribution(claims: list[float]) -> Optional[float]:
    if not claims:
        return None

    numerator = sum(claims)
    denominator = sum(abs(claim) for claim in claims)
    if denominator == 0:
        return 0

    contribution = numerator / denominator
    return max(-1.0, min(1.0, contribution))


def aggregate_evidence(relations_data: list[dict], role: str) -> dict:
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
    if coverage <= 0:
        return 0.0

    return 1 - math.exp(-lambda_param * coverage)


def compute_disagreement(relations_data: list[dict], role: str) -> float:
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

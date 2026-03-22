"""Canonical mapping from LLM confidence label to stored float.

Use this in every code path that converts extraction confidence to a DB value
so that scores are comparable across all ingest routes.
"""

CONFIDENCE_FLOAT: dict[str, float] = {
    "high": 0.8,
    "medium": 0.6,
    "low": 0.4,
}

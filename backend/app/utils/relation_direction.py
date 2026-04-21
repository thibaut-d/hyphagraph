"""
Helpers for normalizing extracted relation polarity into stored direction values.
"""


def canonicalize_finding_polarity(polarity: str | None) -> str | None:
    """
    Map extraction-time finding polarity into the canonical stored direction vocabulary.

    Stored relation directions should remain compatible with inference, which currently
    expects only `supports`, `contradicts`, or `neutral`.
    """
    if polarity == "supports":
        return "supports"
    if polarity == "contradicts":
        return "contradicts"
    if polarity in {"mixed", "neutral", "uncertain"}:
        return "neutral"
    return None

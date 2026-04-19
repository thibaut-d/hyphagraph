"""
Utility for filtering items by confidence level.

Provides type-safe confidence filtering for extracted entities and relations.
"""
from typing import TypeVar, Protocol, Literal


class HasConfidence(Protocol):
    """Protocol for objects that have a confidence attribute."""
    confidence: Literal["high", "medium", "low"]


T = TypeVar("T", bound=HasConfidence)


def filter_by_confidence(
    items: list[T],
    min_confidence: Literal["high", "medium", "low"] | None
) -> list[T]:
    """Filter items by minimum confidence level.

    Args:
        items: List of items with confidence attribute
        min_confidence: Minimum confidence level to include.
                       None = no filtering (return all items)

    Returns:
        Filtered list containing only items meeting minimum confidence.
        If min_confidence is None, returns all items unchanged.

    Examples:
        >>> entities = [Entity(confidence="high"), Entity(confidence="low")]
        >>> filter_by_confidence(entities, "medium")
        [Entity(confidence="high")]

        >>> filter_by_confidence(entities, None)
        [Entity(confidence="high"), Entity(confidence="low")]
    """
    if min_confidence is None:
        return items

    # Define confidence ordering (higher number = higher confidence)
    confidence_order = {"high": 3, "medium": 2, "low": 1}
    min_level = confidence_order.get(min_confidence, 1)

    return [
        item for item in items
        if confidence_order.get(item.confidence, 0) >= min_level
    ]

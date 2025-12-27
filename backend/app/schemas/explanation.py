"""
Schemas for explainability API responses.

Provides detailed explanations of computed inferences,
including source chain, confidence breakdown, and contradictions.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID


class SourceContribution(BaseModel):
    """Details of a single source's contribution to the inference."""

    # Source metadata
    source_id: UUID
    source_title: str
    source_authors: Optional[List[str]] = None
    source_year: Optional[int] = None
    source_kind: str
    source_trust: Optional[float] = None
    source_url: str

    # Relation metadata
    relation_id: UUID
    relation_kind: str
    relation_direction: str
    relation_confidence: float
    relation_scope: Optional[Dict[str, Any]] = None

    # Contribution analysis
    role_weight: Optional[float] = Field(
        None,
        description="Weight of this role within the relation (0-1)",
    )
    contribution_percentage: float = Field(
        ...,
        description="Percentage of total evidence this source contributes",
    )

    class Config:
        from_attributes = True


class ContradictionDetail(BaseModel):
    """Details about contradictory evidence."""

    supporting_sources: List[SourceContribution] = Field(
        default_factory=list,
        description="Sources that support the positive inference",
    )
    contradicting_sources: List[SourceContribution] = Field(
        default_factory=list,
        description="Sources that contradict (oppose) the inference",
    )
    disagreement_score: float = Field(
        ...,
        description="Measure of disagreement between sources (0-1)",
    )

    class Config:
        from_attributes = True


class ConfidenceFactor(BaseModel):
    """Breakdown of confidence contributors."""

    factor: str = Field(
        ...,
        description="Name of the confidence factor (e.g., 'coverage', 'trust')",
    )
    value: float = Field(
        ...,
        description="Numerical value of this factor",
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of what this factor means",
    )

    class Config:
        from_attributes = True


class ExplanationRead(BaseModel):
    """Comprehensive explanation of a computed inference."""

    # Core inference data
    entity_id: UUID
    role_type: str
    score: Optional[float] = Field(
        None,
        description="Normalized inference score in [-1, 1]",
    )
    confidence: float = Field(
        ...,
        description="Confidence in the inference (0-1)",
    )
    disagreement: float = Field(
        ...,
        description="Measure of source contradiction (0-1)",
    )

    # Explanation components
    summary: str = Field(
        ...,
        description="Natural language summary of the inference",
    )
    confidence_factors: List[ConfidenceFactor] = Field(
        default_factory=list,
        description="Breakdown of what contributes to the confidence score",
    )
    contradictions: Optional[ContradictionDetail] = Field(
        None,
        description="Details about contradictory evidence, if any",
    )
    source_chain: List[SourceContribution] = Field(
        default_factory=list,
        description="Full source chain with provenance information",
    )
    scope_filter: Optional[Dict[str, Any]] = Field(
        None,
        description="Scope filter applied to this explanation",
    )

    class Config:
        from_attributes = True

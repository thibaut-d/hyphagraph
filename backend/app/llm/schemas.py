"""
Pydantic schemas for LLM extraction responses.

Defines structured schemas for:
- Entity extraction
- Relation extraction
- Claim extraction
- Entity linking
"""
from typing import Literal
from pydantic import BaseModel, Field


# =============================================================================
# Entity Extraction Schemas
# =============================================================================

EntityCategory = Literal[
    "drug",
    "disease",
    "symptom",
    "biological_mechanism",
    "treatment",
    "biomarker",
    "population",
    "outcome",
    "other"
]

ConfidenceLevel = Literal["high", "medium", "low"]


class ExtractedEntity(BaseModel):
    """
    Schema for an extracted entity from text.

    Represents a single entity identified by the LLM with metadata
    about the extraction quality and source.
    """
    slug: str = Field(
        ...,
        description="Unique identifier for the entity (lowercase, hyphenated)",
        pattern=r"^[a-z][a-z0-9-]*$",
        min_length=3,
        max_length=100
    )
    summary: str | None = Field(
        None,
        description="Brief description of the entity (1-2 sentences)",
        min_length=10,
        max_length=500
    )
    category: EntityCategory = Field(
        ...,
        description="Type of entity"
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Confidence level in this extraction"
    )
    text_span: str = Field(
        ...,
        description="Exact text from source that mentions this entity",
        min_length=1,
        max_length=500
    )


class EntityExtractionResponse(BaseModel):
    """Response schema for entity extraction."""
    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="List of extracted entities"
    )


# =============================================================================
# Relation Extraction Schemas
# =============================================================================

RelationType = Literal[
    "treats",
    "causes",
    "prevents",
    "increases_risk",
    "decreases_risk",
    "mechanism",
    "contraindicated",
    "interacts_with",
    "metabolized_by",
    "biomarker_for",
    "affects_population",
    "measures",  # For diagnostic tools, assessments, biomarkers
    "other"
]


class ExtractedRelation(BaseModel):
    """
    Schema for an extracted relation between entities.

    Represents a relationship identified by the LLM with contextual
    information and source attribution.
    """
    subject_slug: str = Field(
        ...,
        description="Entity slug for the subject of the relation"
    )
    relation_type: RelationType = Field(
        ...,
        description="Type of relation between entities"
    )
    object_slug: str = Field(
        ...,
        description="Entity slug for the object of the relation"
    )
    roles: dict[str, str] = Field(
        default_factory=dict,
        description="Additional context (dosage, route, duration, effect_size, etc.)"
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Confidence level in this extraction"
    )
    text_span: str = Field(
        ...,
        description="Exact text that states this relation",
        min_length=1,
        max_length=1000
    )
    notes: str | None = Field(
        None,
        description="Important caveats, conditions, or context",
        max_length=500
    )


class RelationExtractionResponse(BaseModel):
    """Response schema for relation extraction."""
    relations: list[ExtractedRelation] = Field(
        default_factory=list,
        description="List of extracted relations"
    )


# =============================================================================
# Claim Extraction Schemas
# =============================================================================

ClaimType = Literal[
    "efficacy",
    "safety",
    "mechanism",
    "epidemiology",
    "other"
]

EvidenceStrength = Literal[
    "strong",      # RCTs, meta-analyses
    "moderate",    # Observational studies
    "weak",        # Case reports, small studies
    "anecdotal"    # Individual experiences
]


class ExtractedClaim(BaseModel):
    """
    Schema for an extracted factual claim.

    Represents a specific factual statement from the source with
    information about evidence quality and involved entities.
    """
    claim_text: str = Field(
        ...,
        description="The factual statement being made",
        min_length=10,
        max_length=1000
    )
    entities_involved: list[str] = Field(
        ...,
        description="List of entity slugs mentioned in the claim",
        min_items=1
    )
    claim_type: ClaimType = Field(
        ...,
        description="Type of claim"
    )
    evidence_strength: EvidenceStrength = Field(
        ...,
        description="Strength of evidence supporting the claim"
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Confidence in extracting this claim"
    )
    text_span: str = Field(
        ...,
        description="Exact text supporting this claim",
        min_length=1,
        max_length=2000
    )


class ClaimExtractionResponse(BaseModel):
    """Response schema for claim extraction."""
    claims: list[ExtractedClaim] = Field(
        default_factory=list,
        description="List of extracted claims"
    )


# =============================================================================
# Batch Extraction Schema (All-in-One)
# =============================================================================

class BatchExtractionResponse(BaseModel):
    """
    Response schema for batch extraction of all knowledge.

    Contains entities, relations, and claims extracted from
    a single piece of text in one pass.
    """
    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted entities"
    )
    relations: list[ExtractedRelation] = Field(
        default_factory=list,
        description="Extracted relations"
    )
    claims: list[ExtractedClaim] = Field(
        default_factory=list,
        description="Extracted claims"
    )


# =============================================================================
# Entity Linking Schema
# =============================================================================

class EntityLinkingResponse(BaseModel):
    """
    Response schema for entity linking.

    Maps extracted entity mentions to existing entities in the
    knowledge base or marks them as new entities.
    """
    links: dict[str, str] = Field(
        ...,
        description="Mapping from mention text to entity ID or 'NEW'"
    )


# =============================================================================
# Helper Functions for Validation
# =============================================================================

def validate_entity_extraction(data: dict) -> EntityExtractionResponse:
    """
    Validate and parse entity extraction response from LLM.

    Args:
        data: Raw JSON response from LLM

    Returns:
        Validated EntityExtractionResponse

    Raises:
        ValidationError: If data doesn't match schema
    """
    # Handle case where LLM returns array directly instead of {"entities": [...]}
    if isinstance(data, list):
        data = {"entities": data}

    return EntityExtractionResponse.model_validate(data)


def validate_relation_extraction(data: dict) -> RelationExtractionResponse:
    """Validate and parse relation extraction response from LLM."""
    if isinstance(data, list):
        data = {"relations": data}

    return RelationExtractionResponse.model_validate(data)


def validate_claim_extraction(data: dict) -> ClaimExtractionResponse:
    """Validate and parse claim extraction response from LLM."""
    if isinstance(data, list):
        data = {"claims": data}

    return ClaimExtractionResponse.model_validate(data)


def validate_batch_extraction(data: dict) -> BatchExtractionResponse:
    """Validate and parse batch extraction response from LLM."""
    return BatchExtractionResponse.model_validate(data)


def validate_entity_linking(data: dict) -> EntityLinkingResponse:
    """Validate and parse entity linking response from LLM."""
    # Handle case where LLM returns links directly instead of {"links": {...}}
    if not isinstance(data, dict) or "links" not in data:
        data = {"links": data}

    return EntityLinkingResponse.model_validate(data)

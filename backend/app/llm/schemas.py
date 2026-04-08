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

from app.schemas.common_types import JsonObject, JsonValue


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


class ExtractedRole(BaseModel):
    """Single role in a relation with semantic type."""
    entity_slug: str = Field(
        ...,
        description="Entity slug participating in this role",
        pattern=r"^[a-z][a-z0-9-]*$",
        min_length=2
    )
    role_type: str = Field(
        ...,
        description="Semantic role type (agent, target, population, mechanism, etc.)"
    )


class ExtractedRelation(BaseModel):
    """
    Schema for an extracted N-ary relation with semantic roles.

    Represents a hypergraph edge connecting multiple entities with explicit roles.
    """
    relation_type: RelationType = Field(
        ...,
        description="Type of relation between entities"
    )
    roles: list[ExtractedRole] = Field(
        ...,
        description="Array of entities with their semantic roles (agent, target, population, etc.)",
        min_length=2  # At least 2 entities per relation
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
    study_context: "ExtractedRelationStudyContext | None" = Field(
        None,
        description=(
            "Structured study metadata describing whether this relation is a finding, "
            "hypothesis, background statement, or methodology note, plus proof-level qualifiers"
        ),
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

StatementKind = Literal[
    "finding",
    "background",
    "hypothesis",
    "methodology",
]

FindingPolarity = Literal[
    "supports",
    "contradicts",
    "mixed",
    "neutral",
    "uncertain",
]

StudyDesign = Literal[
    "meta_analysis",
    "systematic_review",
    "randomized_controlled_trial",
    "nonrandomized_trial",
    "cohort_study",
    "case_control_study",
    "cross_sectional_study",
    "case_series",
    "case_report",
    "guideline",
    "review",
    "animal_study",
    "in_vitro",
    "background",
    "unknown",
]


class ExtractedRelationStudyContext(BaseModel):
    """Structured context describing the evidentiary status of an extracted relation."""

    statement_kind: StatementKind = Field(
        ...,
        description=(
            "Whether the relation is a concrete finding, a hypothesis/assumption, "
            "background context, or methodology note"
        ),
    )
    finding_polarity: FindingPolarity | None = Field(
        None,
        description=(
            "Whether the source supports, contradicts, or presents mixed/uncertain evidence for the relation"
        ),
    )
    evidence_strength: EvidenceStrength | None = Field(
        None,
        description="Conservative evidence strength for this relation when supported by the source",
    )
    study_design: StudyDesign | None = Field(
        None,
        description="Study design explicitly stated or directly signaled by the source text",
    )
    sample_size: int | None = Field(
        None,
        ge=1,
        le=10000000,
        description="Participant count when explicitly stated",
    )
    sample_size_text: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Exact source wording for the participant count or study size",
    )
    assertion_text: str | None = Field(
        None,
        min_length=5,
        max_length=500,
        description="Core source-bounded statement for this relation",
    )
    methodology_text: str | None = Field(
        None,
        min_length=5,
        max_length=300,
        description="Short note about methodology or applicability limits explicitly stated in the source",
    )
    statistical_support: str | None = Field(
        None,
        min_length=2,
        max_length=200,
        description="Statistical support snippet when the source provides one, such as p-values or effect sizes",
    )


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
        min_length=1
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

def validate_entity_extraction(data: JsonObject) -> EntityExtractionResponse:
    """
    Validate and parse entity extraction response from LLM.

    Args:
        data: Raw JSON response from LLM (must be a JSON object with "entities" key)

    Returns:
        Validated EntityExtractionResponse

    Raises:
        ValidationError: If data doesn't match schema
    """
    return EntityExtractionResponse.model_validate(data)


def validate_relation_extraction(data: JsonObject) -> RelationExtractionResponse:
    """Validate and parse relation extraction response from LLM."""
    return RelationExtractionResponse.model_validate(data)


def validate_claim_extraction(data: JsonObject) -> ClaimExtractionResponse:
    """Validate and parse claim extraction response from LLM."""
    return ClaimExtractionResponse.model_validate(data)


def validate_batch_extraction(data: JsonObject) -> BatchExtractionResponse:
    """Validate and parse batch extraction response from LLM."""
    # Convert old subject/object format to new roles format for backward compatibility
    if "relations" in data:
        for relation in data["relations"]:
            # If relation has subject_slug/object_slug but no roles array, convert it
            if "subject_slug" in relation and "object_slug" in relation and "roles" not in relation:
                # Map subject/object to semantic roles based on relation type
                relation_type = relation.get("relation_type", "other")

                # Default mapping (can be refined per relation type)
                subject_role = "agent"  # Default
                object_role = "target"   # Default

                # Refine based on relation type
                if relation_type == "biomarker_for":
                    subject_role = "biomarker"
                    object_role = "target"
                elif relation_type == "measures":
                    subject_role = "measured_by"
                    object_role = "target"

                # Create roles array
                relation["roles"] = [
                    {"entity_slug": relation["subject_slug"], "role_type": subject_role},
                    {"entity_slug": relation["object_slug"], "role_type": object_role}
                ]

    return BatchExtractionResponse.model_validate(data)


ExtractedRelation.model_rebuild()


def validate_entity_linking(data: JsonObject) -> EntityLinkingResponse:
    """Validate and parse entity linking response from LLM."""
    if isinstance(data, list):
        raise TypeError("Entity linking response must be a JSON object")

    # Handle case where LLM returns links directly instead of {"links": {...}}
    if not isinstance(data, dict) or "links" not in data:
        data = {"links": data}

    return EntityLinkingResponse.model_validate(data)

"""
Pydantic schemas for LLM extraction responses.

Defines structured schemas for:
- Entity extraction
- Relation extraction
- Entity linking
"""
import re
from typing import Literal
from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

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


def _normalize_extracted_slug(value: object) -> object:
    """
    Normalize LLM-emitted slugs into the canonical lowercase hyphenated form.

    The extraction prompt asks for stable slugs, but model outputs can still
    include uppercase acronyms, punctuation, or leading digits such as
    `5-hydroxytryptophan` or `30-percent-pain-relief`. Normalize those values
    at the schema boundary so one malformed slug does not reject the whole batch.
    """
    if not isinstance(value, str):
        return value

    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")

    if normalized and not normalized[0].isalpha():
        normalized = f"item-{normalized}"

    return normalized or value


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

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: object) -> object:
        return _normalize_extracted_slug(value)


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

_REQUIRED_RELATION_ROLE_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    "treats": (("agent",), ("target",)),
    "causes": (("agent",), ("target", "outcome")),
    "prevents": (("agent",), ("target", "outcome")),
    "increases_risk": (("agent", "condition"), ("target", "outcome")),
    "decreases_risk": (("agent", "condition"), ("target", "outcome")),
    "contraindicated": (("agent",), ("target", "condition")),
    "metabolized_by": (("agent",), ("target", "mechanism")),
    "biomarker_for": (("biomarker",), ("target", "condition")),
    "measures": (("measured_by",), ("target", "outcome", "condition")),
}


def get_missing_required_relation_roles(
    relation_type: str,
    role_types: list[str],
) -> list[tuple[str, ...]]:
    normalized_roles = set(role_types)
    required_groups = _REQUIRED_RELATION_ROLE_GROUPS.get(relation_type, ())
    return [
        role_group
        for role_group in required_groups
        if not any(role_type in normalized_roles for role_type in role_group)
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

    @field_validator("entity_slug", mode="before")
    @classmethod
    def normalize_entity_slug(cls, value: object) -> object:
        return _normalize_extracted_slug(value)


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
    scope: JsonObject | None = Field(
        None,
        description=(
            "Applicability qualifiers for this relation, such as population, dosage, "
            "duration, comparator, or condition"
        ),
    )
    evidence_context: "ExtractedRelationEvidenceContext | None" = Field(
        None,
        validation_alias=AliasChoices("evidence_context", "study_context"),
        description=(
            "Structured evidence metadata describing whether this relation is a finding, "
            "hypothesis, background statement, or methodology note, plus proof-level qualifiers"
        ),
    )

    @property
    def study_context(self) -> "ExtractedRelationEvidenceContext | None":
        """Backward-compatible alias for callers still using the old field name."""
        return self.evidence_context

    @model_validator(mode="after")
    def validate_required_core_roles(self) -> "ExtractedRelation":
        missing_role_groups = get_missing_required_relation_roles(
            self.relation_type,
            [role.role_type for role in self.roles],
        )
        if missing_role_groups:
            missing_labels = [
                " or ".join(role_group)
                for role_group in missing_role_groups
            ]
            raise ValueError(
                f"relation_type '{self.relation_type}' is missing required core roles: "
                f"{', '.join(missing_labels)}"
            )
        return self


class RelationExtractionResponse(BaseModel):
    """Response schema for relation extraction."""
    relations: list[ExtractedRelation] = Field(
        default_factory=list,
        description="List of extracted relations"
    )


EvidenceStrength = Literal[
    "strong",      # RCTs, meta-analyses
    "moderate",    # Observational studies
    "weak",        # Case reports, small studies
    "anecdotal"    # Individual experiences
]


def _normalize_evidence_strength_alias(value: object) -> object:
    """
    Normalize common confidence-style aliases into the evidence-strength vocabulary.

    Some model responses still emit `high`/`medium`/`low` even though the prompt
    asks for `strong`/`moderate`/`weak`. Accepting those aliases keeps the
    extraction pipeline robust without broadening the stored contract.
    """
    if not isinstance(value, str):
        return value

    normalized = value.strip().lower()
    aliases = {
        "high": "strong",
        "medium": "moderate",
        "low": "weak",
    }
    return aliases.get(normalized, normalized)


def _normalize_sample_size(value: object) -> object:
    """Extract an integer participant count from common free-text sample-size formats."""
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return value

    match = re.search(r"\d[\d,]*", value)
    if not match:
        return value

    return int(match.group(0).replace(",", ""))

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


class ExtractedRelationEvidenceContext(BaseModel):
    """Structured context describing the evidentiary status of an extracted relation."""

    @field_validator("evidence_strength", mode="before")
    @classmethod
    def normalize_evidence_strength(cls, value: object) -> object:
        return _normalize_evidence_strength_alias(value)

    @field_validator("sample_size", mode="before")
    @classmethod
    def normalize_sample_size(cls, value: object) -> object:
        return _normalize_sample_size(value)

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


ExtractedRelationStudyContext = ExtractedRelationEvidenceContext

# =============================================================================
# Batch Extraction Schema (All-in-One)
# =============================================================================

class BatchExtractionResponse(BaseModel):
    """
    Response schema for batch extraction of all knowledge.

    Contains entities and relations extracted from
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

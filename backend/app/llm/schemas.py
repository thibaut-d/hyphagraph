"""
Pydantic schemas for LLM extraction responses.

Defines structured schemas for:
- Entity extraction
- Relation extraction
- Entity linking
"""
import logging
import re
from typing import Literal
from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

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

_VALID_ENTITY_CATEGORIES: frozenset[str] = frozenset(EntityCategory.__args__)  # type: ignore[attr-defined]

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

    @field_validator("category", mode="before")
    @classmethod
    def coerce_entity_category(cls, value: object) -> object:
        if isinstance(value, str) and value not in _VALID_ENTITY_CATEGORIES:
            logger.warning("Unknown entity category %r — coercing to 'other'", value)
            return "other"
        return value


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
    "measures",    # Quantifies a value (e.g. MMSE measures cognitive function)
    "diagnoses",   # Confirms presence/absence of a condition (binary clinical decision)
    "predicts",    # Forecasts a future clinical outcome (prognosis)
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
    "diagnoses": (("measured_by",), ("target", "condition")),
    "predicts": (("agent", "biomarker"), ("target", "outcome")),
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
    source_mention: str | None = Field(
        None,
        description=(
            "Shortest exact local source mention for this role participant inside the relation text span"
        ),
        min_length=1,
        max_length=200,
    )

    @field_validator("entity_slug", mode="before")
    @classmethod
    def normalize_entity_slug(cls, value: object) -> object:
        return _normalize_extracted_slug(value)


_VALID_RELATION_TYPES: frozenset[str] = frozenset(RelationType.__args__)  # type: ignore[attr-defined]


class ExtractedRelation(BaseModel):
    """
    Schema for an extracted N-ary relation with semantic roles.

    Represents a hypergraph edge connecting multiple entities with explicit roles.
    """

    # Stores the type name the model originally proposed when it was not in the
    # controlled vocabulary. Populated automatically by coerce_relation_type.
    # Preserved in extraction_data JSON so the review UI can display it and
    # offer a "Propose as new type" path.
    model_proposed_type: str | None = Field(
        None,
        description="Relation type originally proposed by the model when it was not in the controlled vocabulary",
    )

    @field_validator("relation_type", mode="before")
    @classmethod
    def coerce_relation_type(cls, value: object) -> object:
        """Map unknown relation types to 'other'; the original value is captured in model_proposed_type."""
        if isinstance(value, str) and value not in _VALID_RELATION_TYPES:
            logger.warning("Unknown relation_type %r — coercing to 'other'", value)
            # Store the original value in model_proposed_type via model_validator below
            return "other"
        return value

    @model_validator(mode="before")
    @classmethod
    def capture_proposed_type(cls, data: object) -> object:
        """Before field validation: if relation_type is unknown, save it to model_proposed_type."""
        if not isinstance(data, dict):
            return data
        rt = data.get("relation_type")
        if isinstance(rt, str) and rt not in _VALID_RELATION_TYPES:
            data = dict(data)
            data.setdefault("model_proposed_type", rt)
        return data

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


def _normalize_study_design(value: object) -> object:
    """
    Map free-text study-design descriptions to enum values.

    LLMs frequently return verbose phrases like "systematic review and
    meta-analysis of randomized controlled trials" instead of a single
    enum token. This function normalises the most common patterns so
    Pydantic validation does not reject valid extractions.

    Priority order when the text matches multiple keywords: meta_analysis >
    systematic_review > randomized_controlled_trial > nonrandomized_trial >
    cohort_study > case_control_study > cross_sectional_study > case_series >
    case_report > guideline > review > animal_study > in_vitro > background.
    """
    if not isinstance(value, str):
        return value

    v = value.strip().lower()

    # Already a valid enum token — pass through unchanged.
    _valid = {
        "meta_analysis", "systematic_review", "randomized_controlled_trial",
        "nonrandomized_trial", "cohort_study", "case_control_study",
        "cross_sectional_study", "case_series", "case_report", "guideline",
        "review", "animal_study", "in_vitro", "background", "unknown",
    }
    if v in _valid:
        return v

    # Keyword-based heuristics (highest-specificity first).
    if "meta-analysis" in v or "meta analysis" in v or "meta_analysis" in v:
        return "meta_analysis"
    if "systematic review" in v or "systematic_review" in v:
        return "systematic_review"
    if "randomized controlled trial" in v or "randomised controlled trial" in v or "rct" == v:
        return "randomized_controlled_trial"
    if "nonrandomized" in v or "non-randomized" in v or "non randomized" in v:
        return "nonrandomized_trial"
    if "cohort" in v:
        return "cohort_study"
    if "case-control" in v or "case control" in v:
        return "case_control_study"
    if "cross-sectional" in v or "cross sectional" in v:
        return "cross_sectional_study"
    if "case series" in v or "case_series" in v:
        return "case_series"
    if "case report" in v or "case_report" in v:
        return "case_report"
    if "guideline" in v:
        return "guideline"
    if "animal" in v:
        return "animal_study"
    if "in vitro" in v or "in_vitro" in v:
        return "in_vitro"
    if "review" in v:
        return "review"
    if "background" in v:
        return "background"

    # Cannot map — return original value so Pydantic emits the validation
    # error with the actual bad input rather than a silent None.
    return value


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

    @field_validator("study_design", mode="before")
    @classmethod
    def normalize_study_design(cls, value: object) -> object:
        return _normalize_study_design(value)

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
        max_length=300,
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

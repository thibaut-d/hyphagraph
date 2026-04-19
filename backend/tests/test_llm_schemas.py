import pytest
from pydantic import ValidationError

from app.api.document_extraction_dependencies import raise_internal_api_exception
from app.llm.schemas import validate_batch_extraction
from app.utils.errors import AppException, ErrorCode


def test_validate_batch_extraction_normalizes_confidence_style_evidence_strength_aliases():
    result = validate_batch_extraction(
        {
            "entities": [
                {
                    "slug": "duloxetine",
                    "summary": "Duloxetine is an antidepressant evaluated in the source.",
                    "category": "drug",
                    "confidence": "high",
                    "text_span": "duloxetine",
                },
                {
                    "slug": "chronic-pain",
                    "summary": "Chronic pain is the condition discussed in the source.",
                    "category": "disease",
                    "confidence": "high",
                    "text_span": "chronic pain",
                },
            ],
            "relations": [
                {
                    "relation_type": "treats",
                    "roles": [
                        {"entity_slug": "duloxetine", "role_type": "agent"},
                        {"entity_slug": "chronic-pain", "role_type": "target"},
                    ],
                    "confidence": "medium",
                    "text_span": "duloxetine improved chronic pain outcomes",
                    "evidence_context": {
                        "statement_kind": "finding",
                        "finding_polarity": "supports",
                        "evidence_strength": "low",
                    },
                }
            ],
        }
    )

    assert result.relations[0].evidence_context is not None
    assert result.relations[0].evidence_context.evidence_strength == "weak"


def test_validate_batch_extraction_normalizes_slug_shapes_before_schema_validation():
    result = validate_batch_extraction(
        {
            "entities": [
                {
                    "slug": "5-hydroxytryptophan",
                    "summary": "5-HTP is discussed as a treatment option in the source.",
                    "category": "drug",
                    "confidence": "high",
                    "text_span": "5-hydroxytryptophan",
                },
                {
                    "slug": "GRADE",
                    "summary": "GRADE is the evidence framework referenced by the review.",
                    "category": "other",
                    "confidence": "medium",
                    "text_span": "GRADE",
                },
            ],
            "relations": [
                {
                    "relation_type": "treats",
                    "roles": [
                        {"entity_slug": "5-hydroxytryptophan", "role_type": "agent"},
                        {"entity_slug": "30-percent-pain-relief", "role_type": "target"},
                    ],
                    "confidence": "medium",
                    "text_span": "5-hydroxytryptophan improved 30 percent pain relief",
                }
            ],
        }
    )

    assert result.entities[0].slug == "item-5-hydroxytryptophan"
    assert result.entities[1].slug == "grade"
    assert result.relations[0].roles[0].entity_slug == "item-5-hydroxytryptophan"
    assert result.relations[0].roles[1].entity_slug == "item-30-percent-pain-relief"


def test_validate_batch_extraction_normalizes_textual_sample_size_to_integer():
    result = validate_batch_extraction(
        {
            "entities": [
                {
                    "slug": "duloxetine",
                    "summary": "Duloxetine is the active treatment discussed in the source.",
                    "category": "drug",
                    "confidence": "high",
                    "text_span": "duloxetine",
                },
                {
                    "slug": "fibromyalgia",
                    "summary": "Fibromyalgia is the target condition in the source.",
                    "category": "disease",
                    "confidence": "high",
                    "text_span": "fibromyalgia",
                },
            ],
            "relations": [
                {
                    "relation_type": "treats",
                    "roles": [
                        {"entity_slug": "duloxetine", "role_type": "agent"},
                        {"entity_slug": "fibromyalgia", "role_type": "target"},
                    ],
                    "confidence": "medium",
                    "text_span": "duloxetine improved fibromyalgia outcomes",
                    "study_context": {
                        "statement_kind": "finding",
                        "sample_size": "1,474 participants",
                    },
                }
            ],
        }
    )

    assert result.relations[0].evidence_context is not None
    assert result.relations[0].evidence_context.sample_size == 1474


def test_validate_batch_extraction_accepts_legacy_study_context_but_serializes_evidence_context():
    result = validate_batch_extraction(
        {
            "entities": [
                {
                    "slug": "aspirin",
                    "summary": "Aspirin is the active treatment mentioned in the source.",
                    "category": "drug",
                    "confidence": "high",
                    "text_span": "aspirin",
                },
                {
                    "slug": "pain",
                    "summary": "Pain is the target symptom discussed in the source.",
                    "category": "symptom",
                    "confidence": "high",
                    "text_span": "pain",
                },
            ],
            "relations": [
                {
                    "relation_type": "treats",
                    "roles": [
                        {"entity_slug": "aspirin", "role_type": "agent"},
                        {"entity_slug": "pain", "role_type": "target"},
                    ],
                    "confidence": "high",
                    "text_span": "aspirin reduced pain",
                    "study_context": {
                        "statement_kind": "finding",
                        "evidence_strength": "strong",
                    },
                }
            ],
        }
    )

    relation_dump = result.relations[0].model_dump()

    assert result.relations[0].evidence_context is not None
    assert relation_dump["evidence_context"]["statement_kind"] == "finding"
    assert "study_context" not in relation_dump


def test_validate_batch_extraction_preserves_optional_role_source_mentions():
    result = validate_batch_extraction(
        {
            "entities": [
                {
                    "slug": "selective-serotonin-reuptake-inhibitors",
                    "summary": "Selective serotonin reuptake inhibitor drug class.",
                    "category": "drug",
                    "confidence": "high",
                    "text_span": "selective serotonin reuptake inhibitors (SSRIs)",
                },
                {
                    "slug": "pain",
                    "summary": "Pain outcome discussed in the source.",
                    "category": "outcome",
                    "confidence": "high",
                    "text_span": "pain",
                },
            ],
            "relations": [
                {
                    "relation_type": "treats",
                    "roles": [
                        {
                            "entity_slug": "selective-serotonin-reuptake-inhibitors",
                            "role_type": "agent",
                            "source_mention": "SSRIs",
                        },
                        {
                            "entity_slug": "pain",
                            "role_type": "target",
                            "source_mention": "pain",
                        },
                    ],
                    "confidence": "high",
                    "text_span": "SSRIs reduced pain compared with placebo.",
                }
            ],
        }
    )

    assert result.relations[0].roles[0].source_mention == "SSRIs"
    assert result.relations[0].roles[1].source_mention == "pain"


def test_validate_batch_extraction_rejects_causes_relation_without_agent():
    with pytest.raises(ValidationError) as exc_info:
        validate_batch_extraction(
            {
                "entities": [
                    {
                        "slug": "nausea",
                        "summary": "Nausea is the adverse event mentioned in the source.",
                        "category": "symptom",
                        "confidence": "high",
                        "text_span": "nausea",
                    },
                    {
                        "slug": "placebo",
                        "summary": "Placebo is the comparator mentioned in the source.",
                        "category": "other",
                        "confidence": "high",
                        "text_span": "placebo",
                    },
                ],
                "relations": [
                    {
                        "relation_type": "causes",
                        "roles": [
                            {"entity_slug": "nausea", "role_type": "target"},
                            {"entity_slug": "placebo", "role_type": "control_group"},
                        ],
                        "confidence": "medium",
                        "text_span": "adverse events experienced by participants were not serious",
                    }
                ],
            }
        )

    assert "missing required core roles" in str(exc_info.value)


def test_validate_batch_extraction_normalizes_verbose_study_design_phrases():
    """LLMs often return prose like 'systematic review and meta-analysis of RCTs'
    instead of a single enum token.  The normalizer must map the highest-specificity
    keyword it finds to the correct enum value."""
    result = validate_batch_extraction(
        {
            "entities": [
                {
                    "slug": "duloxetine",
                    "summary": "Duloxetine is the active treatment discussed in the source.",
                    "category": "drug",
                    "confidence": "high",
                    "text_span": "duloxetine",
                },
                {
                    "slug": "fibromyalgia",
                    "summary": "Fibromyalgia is the target condition in the source.",
                    "category": "disease",
                    "confidence": "high",
                    "text_span": "fibromyalgia",
                },
            ],
            "relations": [
                {
                    "relation_type": "treats",
                    "roles": [
                        {"entity_slug": "duloxetine", "role_type": "agent"},
                        {"entity_slug": "fibromyalgia", "role_type": "target"},
                    ],
                    "confidence": "high",
                    "text_span": "duloxetine for fibromyalgia in a systematic review and meta-analysis of randomized controlled trials",
                    "evidence_context": {
                        "statement_kind": "finding",
                        "study_design": "systematic review and meta-analysis of randomized controlled trials",
                    },
                },
                {
                    "relation_type": "treats",
                    "roles": [
                        {"entity_slug": "duloxetine", "role_type": "agent"},
                        {"entity_slug": "fibromyalgia", "role_type": "target"},
                    ],
                    "confidence": "medium",
                    "text_span": "a systematic review of observational data",
                    "evidence_context": {
                        "statement_kind": "finding",
                        "study_design": "systematic review of observational data",
                    },
                },
                {
                    "relation_type": "treats",
                    "roles": [
                        {"entity_slug": "duloxetine", "role_type": "agent"},
                        {"entity_slug": "fibromyalgia", "role_type": "target"},
                    ],
                    "confidence": "medium",
                    "text_span": "a randomized controlled trial",
                    "evidence_context": {
                        "statement_kind": "finding",
                        "study_design": "randomized controlled trial",
                    },
                },
            ],
        }
    )

    assert result.relations[0].evidence_context is not None
    # meta-analysis wins over systematic_review because it has higher priority
    assert result.relations[0].evidence_context.study_design == "meta_analysis"
    assert result.relations[1].evidence_context is not None
    assert result.relations[1].evidence_context.study_design == "systematic_review"
    assert result.relations[2].evidence_context is not None
    assert result.relations[2].evidence_context.study_design == "randomized_controlled_trial"


def test_raise_internal_api_exception_uses_structured_app_exception():
    with pytest.raises(AppException) as exc_info:
        raise_internal_api_exception(
            message="Failed to extract from URL",
            context={"source_id": "source-123"},
        )

    assert exc_info.value.error_detail.code == ErrorCode.INTERNAL_SERVER_ERROR
    assert exc_info.value.error_detail.message == "Failed to extract from URL"
    assert exc_info.value.error_detail.context == {"source_id": "source-123"}

"""
Tests for extraction validation service.

Tests text span validation logic that prevents LLM hallucinations
by verifying extractions are grounded in source text.
"""
import pytest

from app.services.extraction_validation_service import (
    TextSpanValidator,
    ExtractionValidationService,
    ValidationResult,
)
from app.services.batch_extraction_orchestrator import BatchExtractionOrchestrator
from app.llm.schemas import ExtractedEntity, ExtractedRelation, ExtractedRole


# Sample source text for testing
SAMPLE_SOURCE = """
Duloxetine is an FDA-approved medication for fibromyalgia.
Clinical trials showed significant improvement in pain scores compared to placebo.
The study included 874 patients with chronic widespread pain.
Common side effects include nausea, dry mouth, and somnolence.
Duloxetine works by inhibiting serotonin and norepinephrine reuptake.
"""


class TestTextSpanValidator:
    """Test core text span validation logic."""

    def test_exact_match_validates_successfully(self):
        """Test that exact substring matches pass validation."""
        # Arrange
        validator = TextSpanValidator(validation_level="moderate")
        entity = ExtractedEntity(
            slug="duloxetine",
            category="drug",
            confidence="high",
            text_span="Duloxetine is an FDA-approved medication for fibromyalgia"
        )

        # Act
        result = validator.validate_entity(entity, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is True
        assert result.confidence_adjustment == 1.0
        assert result.validation_score == 1.0
        assert result.flags == []
        assert result.matched_span is not None

    def test_case_insensitive_match_validates(self):
        """Test that case-insensitive matches are found."""
        # Arrange
        validator = TextSpanValidator(validation_level="moderate")
        entity = ExtractedEntity(
            slug="fibromyalgia",
            category="disease",
            confidence="high",
            text_span="FIBROMYALGIA"  # Different case
        )

        # Act
        result = validator.validate_entity(entity, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is True
        assert result.validation_score == 1.0

    def test_missing_text_span_fails_validation(self):
        """Test that entities without text spans fail validation."""
        # Arrange
        validator = TextSpanValidator(validation_level="moderate")
        entity = ExtractedEntity(
            slug="invented-drug",
            category="drug",
            confidence="high",
            text_span="This text does not exist in the source"
        )

        # Act
        result = validator.validate_entity(entity, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is True  # In moderate mode, still valid but flagged
        assert result.confidence_adjustment < 1.0  # Confidence degraded
        assert "text_span_not_found" in result.flags

    def test_strict_mode_rejects_missing_spans(self):
        """Test that strict mode rejects extractions with missing text spans."""
        # Arrange
        validator = TextSpanValidator(validation_level="strict")
        entity = ExtractedEntity(
            slug="hallucinated",
            category="drug",
            confidence="high",
            text_span="This is completely made up"
        )

        # Act
        result = validator.validate_entity(entity, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is False
        assert result.confidence_adjustment == 0.0
        assert "possible_hallucination" in result.flags

    def test_lenient_mode_accepts_missing_spans(self):
        """Test that lenient mode accepts missing spans with degraded confidence."""
        # Arrange
        validator = TextSpanValidator(validation_level="lenient")
        entity = ExtractedEntity(
            slug="uncertain",
            category="drug",
            confidence="medium",
            text_span="Not in source"
        )

        # Act
        result = validator.validate_entity(entity, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is True
        assert result.confidence_adjustment > 0.0  # Some confidence retained
        assert result.confidence_adjustment < 1.0  # But degraded

    def test_fuzzy_match_with_punctuation_differences(self):
        """Test that fuzzy matching handles punctuation variations."""
        # Arrange
        validator = TextSpanValidator(validation_level="moderate", allow_fuzzy_match=True)
        entity = ExtractedEntity(
            slug="duloxetine",
            category="drug",
            confidence="high",
            # Source has period, this doesn't
            text_span="Duloxetine is an FDA-approved medication for fibromyalgia"
        )

        # Act
        result = validator.validate_entity(entity, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is True
        assert result.validation_score >= 0.8

    def test_relation_validation_requires_longer_spans(self):
        """Test that relations require minimum span length."""
        # Arrange
        validator = TextSpanValidator(validation_level="moderate", min_exact_match_length=10)
        relation = ExtractedRelation(
            relation_type="treats",
            roles=[
                {"entity_slug": "duloxetine", "role_type": "agent"},
                {"entity_slug": "fibromyalgia", "role_type": "target"}
            ],
            confidence="high",
            text_span="pain"  # Too short for relation
        )

        # Act
        result = validator.validate_relation(relation, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is False
        assert "text_span_too_short_for_relation" in result.flags

    def test_relation_with_valid_long_span(self):
        """Test that relations with valid long spans pass."""
        # Arrange
        validator = TextSpanValidator(validation_level="moderate")
        relation = ExtractedRelation(
            relation_type="treats",
            roles=[
                {"entity_slug": "duloxetine", "role_type": "agent"},
                {"entity_slug": "chronic-widespread-pain", "role_type": "target"}
            ],
            confidence="high",
            text_span="874 patients with chronic widespread pain"
        )

        # Act
        result = validator.validate_relation(relation, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is True
        assert result.validation_score == 1.0

    def test_relation_validation_rejects_missing_required_core_roles(self):
        """Relations missing their semantic core should be rejected before span validation."""
        validator = TextSpanValidator(validation_level="moderate")
        relation = ExtractedRelation.model_construct(
            relation_type="causes",
            roles=[
                ExtractedRole(entity_slug="nausea", role_type="target"),
                ExtractedRole(entity_slug="placebo", role_type="control_group"),
            ],
            confidence="medium",
            text_span="adverse events experienced by participants were not serious",
            notes="Common adverse event reported.",
            scope=None,
            evidence_context=None,
        )

        result = validator.validate_relation(relation, SAMPLE_SOURCE)

        assert result.is_valid is False
        assert result.confidence_adjustment == 0.0
        assert "missing_required_relation_roles" in result.flags
        assert "missing_core_role:agent" in result.flags

    def test_relation_validation_rejects_contextual_entity_in_required_core_role(self):
        """Contextual pseudo-entities must not satisfy required semantic core roles."""
        validator = TextSpanValidator(validation_level="moderate")
        relation = ExtractedRelation.model_construct(
            relation_type="causes",
            roles=[
                ExtractedRole(entity_slug="sample-size-41", role_type="agent"),
                ExtractedRole(entity_slug="nausea", role_type="target"),
                ExtractedRole(entity_slug="placebo", role_type="control_group"),
            ],
            confidence="medium",
            text_span="adverse events experienced by participants were not serious",
            notes="Common adverse event reported.",
            scope=None,
            evidence_context=None,
        )

        result = validator.validate_relation(relation, SAMPLE_SOURCE)

        assert result.is_valid is False
        assert result.validation_score == 0.0
        assert "invalid_contextual_core_role" in result.flags
        assert "invalid_contextual_core_role:agent:sample-size-41" in result.flags

    def test_relation_validation_rejects_multiple_primary_targets_in_one_relation(self):
        """Collapsed multi-outcome findings should be split, not stored as one relation."""
        validator = TextSpanValidator(validation_level="moderate")
        relation = ExtractedRelation.model_construct(
            relation_type="treats",
            roles=[
                ExtractedRole(entity_slug="ssris", role_type="agent"),
                ExtractedRole(entity_slug="fibromyalgia", role_type="target"),
                ExtractedRole(entity_slug="depression", role_type="target"),
                ExtractedRole(entity_slug="chronic-pain", role_type="target"),
            ],
            confidence="medium",
            text_span=(
                "SSRIs significantly reduced pain and improved depression in fibromyalgia "
                "patients compared to placebo."
            ),
            notes=None,
            scope=None,
            evidence_context=None,
        )

        result = validator.validate_relation(relation, SAMPLE_SOURCE)

        assert result.is_valid is False
        assert "invalid_relation_shape" in result.flags
        assert "too_many_role_group_members:target:3" in result.flags

@pytest.mark.asyncio
class TestExtractionValidationService:
    """Test batch validation service."""

    async def test_validate_entities_batch(self):
        """Test validating a batch of entities."""
        # Arrange
        service = ExtractionValidationService(validation_level="moderate")
        entities = [
            ExtractedEntity(
                slug="duloxetine",
                category="drug",
                confidence="high",
                text_span="Duloxetine is an FDA-approved medication"
            ),
            ExtractedEntity(
                slug="fibromyalgia",
                category="disease",
                confidence="high",
                text_span="fibromyalgia"
            ),
            ExtractedEntity(
                slug="hallucinated",
                category="drug",
                confidence="high",
                text_span="This drug does not exist in source"
            ),
        ]

        # Act
        validated, results = await service.validate_entities(entities, SAMPLE_SOURCE)

        # Assert
        assert len(validated) == 3  # All returned in moderate mode
        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is True
        assert results[2].is_valid is True  # Flagged but not rejected in moderate
        assert len(results[2].flags) > 0  # Has validation flags

    async def test_auto_reject_invalid_entities(self):
        """Test that auto_reject_invalid filters out invalid extractions."""
        # Arrange
        service = ExtractionValidationService(
            validation_level="strict",
            auto_reject_invalid=True
        )
        entities = [
            ExtractedEntity(
                slug="duloxetine",
                category="drug",
                confidence="high",
                text_span="Duloxetine is an FDA-approved medication"
            ),
            ExtractedEntity(
                slug="hallucinated",
                category="drug",
                confidence="high",
                text_span="Completely made up text"
            ),
        ]

        # Act
        validated, results = await service.validate_entities(entities, SAMPLE_SOURCE)

        # Assert
        assert len(validated) == 1  # Only valid entity returned
        assert validated[0].slug == "duloxetine"
        assert len(results) == 2  # But all results tracked
        assert results[0].is_valid is True
        assert results[1].is_valid is False

    async def test_validate_relations_batch(self):
        """Test validating a batch of relations."""
        # Arrange
        service = ExtractionValidationService(validation_level="moderate")
        relations = [
            ExtractedRelation(
                relation_type="treats",
                roles=[
                    {"entity_slug": "duloxetine", "role_type": "agent"},
                    {"entity_slug": "fibromyalgia", "role_type": "target"}
                ],
                confidence="high",
                text_span="Clinical trials showed significant improvement in pain scores"
            ),
            ExtractedRelation(
                relation_type="causes",
                roles=[
                    {"entity_slug": "duloxetine", "role_type": "agent"},
                    {"entity_slug": "nausea", "role_type": "target"}
                ],
                confidence="medium",
                text_span="Common side effects include nausea"
            ),
        ]

        # Act
        validated, results = await service.validate_relations(relations, SAMPLE_SOURCE)

        # Assert
        assert len(validated) == 2
        assert all(r.is_valid for r in results)

    async def test_validate_relations_rejects_locally_ungrounded_context_role(self):
        """Context roles must be justified by the relation span, not by the document overall."""
        service = ExtractionValidationService(validation_level="moderate")
        source_text = "Duloxetine caused nausea in treated participants."
        entities = [
            ExtractedEntity(
                slug="duloxetine",
                category="drug",
                confidence="high",
                text_span="Duloxetine",
            ),
            ExtractedEntity(
                slug="nausea",
                category="symptom",
                confidence="high",
                text_span="nausea",
            ),
            ExtractedEntity(
                slug="placebo",
                category="other",
                confidence="high",
                text_span="placebo",
            ),
        ]
        relations = [
            ExtractedRelation(
                relation_type="causes",
                roles=[
                    {"entity_slug": "duloxetine", "role_type": "agent"},
                    {"entity_slug": "nausea", "role_type": "target"},
                    {"entity_slug": "placebo", "role_type": "control_group"},
                ],
                confidence="medium",
                text_span="Duloxetine caused nausea in treated participants.",
            ),
        ]

        validated, results = await service.validate_relations(
            relations,
            source_text,
            entities=entities,
        )

        assert len(validated) == 1
        assert results[0].is_valid is False
        assert "relation_role_not_grounded_locally" in results[0].flags
        assert "ungrounded_relation_role:control_group:placebo" in results[0].flags

    async def test_validate_relations_accepts_role_source_mentions_for_abbreviations(self):
        """Role-level source mentions should ground abbreviation-heavy local spans."""
        service = ExtractionValidationService(validation_level="moderate")
        source_text = "SSRIs reduced pain compared with placebo."
        entities = [
            ExtractedEntity(
                slug="selective-serotonin-reuptake-inhibitors",
                category="drug",
                confidence="high",
                text_span="selective serotonin reuptake inhibitors (SSRIs)",
            ),
            ExtractedEntity(
                slug="pain",
                category="outcome",
                confidence="high",
                text_span="pain",
            ),
            ExtractedEntity(
                slug="placebo",
                category="other",
                confidence="high",
                text_span="placebo",
            ),
        ]
        relations = [
            ExtractedRelation(
                relation_type="treats",
                roles=[
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
                    {
                        "entity_slug": "placebo",
                        "role_type": "control_group",
                        "source_mention": "placebo",
                    },
                ],
                confidence="high",
                text_span="SSRIs reduced pain compared with placebo.",
            ),
        ]

        validated, results = await service.validate_relations(
            relations,
            source_text,
            entities=entities,
        )

        assert len(validated) == 1
        assert results[0].is_valid is True
        assert results[0].flags == []

    async def test_relation_validation_accepts_parenthetical_entity_variants_without_role_mentions(self):
        """Entity text spans with parenthetical abbreviations should still ground local spans."""
        validator = TextSpanValidator(validation_level="moderate")
        relation = ExtractedRelation(
            relation_type="treats",
            roles=[
                {
                    "entity_slug": "selective-serotonin-reuptake-inhibitors",
                    "role_type": "agent",
                },
                {
                    "entity_slug": "pain",
                    "role_type": "target",
                },
            ],
            confidence="high",
            text_span="SSRIs reduced pain compared with placebo.",
        )
        entity_lookup = {
            "selective-serotonin-reuptake-inhibitors": ExtractedEntity(
                slug="selective-serotonin-reuptake-inhibitors",
                category="drug",
                confidence="high",
                text_span="selective serotonin reuptake inhibitors (SSRIs)",
            ),
            "pain": ExtractedEntity(
                slug="pain",
                category="outcome",
                confidence="high",
                text_span="pain",
            ),
        }

        result = validator.validate_relation(
            relation,
            "SSRIs reduced pain compared with placebo.",
            entity_lookup=entity_lookup,
        )

        assert result.is_valid is True
        assert result.flags == []

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_text_span(self):
        """Test that Pydantic rejects empty text spans."""
        # Arrange
        validator = TextSpanValidator()

        # Act & Assert - Pydantic validation should reject empty strings
        with pytest.raises(Exception):  # Pydantic ValidationError
            entity = ExtractedEntity(
                slug="test",
                category="drug",
                confidence="high",
                text_span=""  # Will be rejected by Pydantic
            )

    def test_very_short_text_span(self):
        """Test handling of very short text spans."""
        # Arrange
        validator = TextSpanValidator()
        entity = ExtractedEntity(
            slug="test",
            category="drug",
            confidence="high",
            text_span="ab"  # Only 2 characters
        )

        # Act
        result = validator.validate_entity(entity, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is False

    def test_text_span_with_special_characters(self):
        """Test handling of text spans with special characters."""
        # Arrange
        validator = TextSpanValidator()
        entity = ExtractedEntity(
            slug="test",
            category="drug",
            confidence="high",
            text_span="FDA-approved"
        )

        # Act
        result = validator.validate_entity(entity, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is True  # Should find "FDA-approved" in source

    def test_unicode_text_handling(self):
        """Test handling of unicode characters."""
        # Arrange
        source_with_unicode = "Café serves naïve patients with fibromyalgia."
        validator = TextSpanValidator()
        entity = ExtractedEntity(
            slug="cafe",
            category="other",
            confidence="medium",
            text_span="Café serves naïve patients"
        )

        # Act
        result = validator.validate_entity(entity, source_with_unicode)

        # Assert
        assert result.is_valid is True


# =============================================================================
# DF-EXT-M6: Entity slug coherence (cross-field semantic validation)
# =============================================================================

def _make_orchestrator(strict: bool = False) -> BatchExtractionOrchestrator:
    """Return an orchestrator with validation enabled but no LLM needed for slug checks."""
    level = "strict" if strict else "moderate"
    return BatchExtractionOrchestrator(
        enable_validation=True,
        validation_level=level,
    )


def _dummy_result(is_valid: bool = True) -> ValidationResult:
    return ValidationResult(
        is_valid=is_valid,
        confidence_adjustment=1.0,
        validation_score=1.0,
        flags=[],
        matched_span=None,
    )


def _make_entities(*slugs: str) -> list[ExtractedEntity]:
    return [
        ExtractedEntity(slug=s, category="drug", confidence="high", text_span=s)
        for s in slugs
    ]


def _make_relation(*slugs: str) -> ExtractedRelation:
    roles = [{"entity_slug": s, "role_type": "agent" if i == 0 else "target"} for i, s in enumerate(slugs)]
    return ExtractedRelation(
        relation_type="treats",
        roles=roles,
        confidence="high",
        text_span="Some relation text span for testing",
    )


class TestEntitySlugCoherence:
    """Unit tests for _check_entity_slug_coherence (DF-EXT-M6)."""

    def test_all_known_slugs_pass_unchanged(self):
        """Relations whose slugs all exist in extracted entities are untouched."""
        orch = _make_orchestrator()
        entities = _make_entities("drug-a", "disease-b")
        relation = _make_relation("drug-a", "disease-b")
        rel_result = _dummy_result()

        rels, rel_results = orch._check_entity_slug_coherence(
            entities, [relation], [rel_result]
        )

        assert len(rels) == 1
        assert rel_results[0].flags == []
        assert rel_results[0].confidence_adjustment == 1.0

    def test_unknown_relation_slug_flagged_in_moderate_mode(self):
        """Relation with an unknown entity slug is flagged and confidence halved (moderate)."""
        orch = _make_orchestrator(strict=False)
        entities = _make_entities("drug-a")
        relation = _make_relation("drug-a", "ghost-entity")
        rel_result = _dummy_result()

        rels, rel_results = orch._check_entity_slug_coherence(
            entities, [relation], [rel_result]
        )

        assert len(rels) == 1  # Still kept in moderate mode
        assert any("unknown_entity_slug" in f for f in rel_results[0].flags)
        assert "ghost-entity" in rel_results[0].flags[0]
        assert rel_results[0].confidence_adjustment == pytest.approx(0.5)
        assert rel_results[0].validation_score == pytest.approx(0.5)

    def test_unknown_relation_slug_rejected_in_strict_mode(self):
        """Relation with unknown entity slug is removed in strict mode."""
        orch = _make_orchestrator(strict=True)
        entities = _make_entities("drug-a")
        relation = _make_relation("drug-a", "ghost-entity")
        rel_result = _dummy_result()

        rels, rel_results = orch._check_entity_slug_coherence(
            entities, [relation], [rel_result]
        )

        assert len(rels) == 0  # Removed in strict mode
        assert len(rel_results) == 0

    def test_empty_entity_list_flags_all_relations(self):
        """When no entities are extracted, all relation slugs are unknown."""
        orch = _make_orchestrator(strict=False)
        relation = _make_relation("drug-a", "disease-b")
        rel_result = _dummy_result()

        rels, rel_results = orch._check_entity_slug_coherence(
            [], [relation], [rel_result]
        )

        assert len(rels) == 1  # Kept in moderate mode
        assert any("unknown_entity_slug" in f for f in rel_results[0].flags)

    def test_multiple_unknown_slugs_all_listed_in_flag(self):
        """All unknown slugs are listed in the flag string."""
        orch = _make_orchestrator(strict=False)
        entities = _make_entities("known")
        relation = _make_relation("known", "ghost-1", "ghost-2")
        rel_result = _dummy_result()

        # Need 3-role relation; create manually
        relation = ExtractedRelation(
            relation_type="treats",
            roles=[
                {"entity_slug": "known", "role_type": "agent"},
                {"entity_slug": "ghost-1", "role_type": "target"},
                {"entity_slug": "ghost-2", "role_type": "population"},
            ],
            confidence="high",
            text_span="Some relation text span for testing",
        )

        rels, rel_results = orch._check_entity_slug_coherence(
            entities, [relation], [rel_result]
        )

        flag = rel_results[0].flags[0]
        assert "ghost-1" in flag
        assert "ghost-2" in flag


@pytest.mark.asyncio
async def test_orchestrator_validation_flags_missing_relation_text_span():
    orch = _make_orchestrator(strict=False)
    entities = _make_entities("duloxetine", "fibromyalgia")
    relation = ExtractedRelation(
        relation_type="treats",
        roles=[
            {"entity_slug": "duloxetine", "role_type": "agent"},
            {"entity_slug": "fibromyalgia", "role_type": "target"},
        ],
        confidence="high",
        text_span="This relation text does not appear in the source",
    )

    _, relations, _, relation_results = await orch._validate_extractions_with_results(
        entities,
        [relation],
        SAMPLE_SOURCE,
    )

    assert len(relations) == 1
    assert any("text_span_not_found" in flag for flag in relation_results[0].flags)

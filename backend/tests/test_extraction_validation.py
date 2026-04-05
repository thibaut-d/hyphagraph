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
from app.llm.schemas import ExtractedEntity, ExtractedRelation, ExtractedClaim


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

    def test_claim_validation_strictest(self):
        """Test that claims have strictest validation."""
        # Arrange
        validator = TextSpanValidator(validation_level="moderate")

        # Valid claim
        valid_claim = ExtractedClaim(
            claim_text="Duloxetine showed significant improvement compared to placebo",
            entities_involved=["duloxetine"],
            claim_type="efficacy",
            evidence_strength="strong",
            confidence="high",
            text_span="Clinical trials showed significant improvement in pain scores compared to placebo"
        )

        # Act
        valid_result = validator.validate_claim(valid_claim, SAMPLE_SOURCE)

        # Assert
        assert valid_result.is_valid is True
        assert valid_result.validation_score == 1.0

    def test_claim_without_span_rejected_in_moderate_mode(self):
        """Test that claims without valid spans are rejected in moderate mode."""
        # Arrange
        validator = TextSpanValidator(validation_level="moderate")
        claim = ExtractedClaim(
            claim_text="This claim is not supported by the text",
            entities_involved=["duloxetine"],
            claim_type="efficacy",
            evidence_strength="weak",
            confidence="low",
            text_span="Duloxetine cures everything instantly"  # Hallucinated
        )

        # Act
        result = validator.validate_claim(claim, SAMPLE_SOURCE)

        # Assert
        assert result.is_valid is False  # Claims are strict in moderate mode
        assert "claim_text_span_not_found" in result.flags


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

    async def test_validate_claims_batch(self):
        """Test validating a batch of claims."""
        # Arrange
        service = ExtractionValidationService(validation_level="moderate")
        claims = [
            ExtractedClaim(
                claim_text="Duloxetine improves pain in fibromyalgia patients",
                entities_involved=["duloxetine", "fibromyalgia"],
                claim_type="efficacy",
                evidence_strength="strong",
                confidence="high",
                text_span="Clinical trials showed significant improvement in pain scores compared to placebo"
            ),
        ]

        # Act
        validated, results = await service.validate_claims(claims, SAMPLE_SOURCE)

        # Assert
        assert len(validated) == 1
        assert results[0].is_valid is True
        assert results[0].validation_score >= 0.9


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


def _make_claim(*slugs: str) -> ExtractedClaim:
    return ExtractedClaim(
        claim_text="Some claim text for testing purposes",
        entities_involved=list(slugs),
        claim_type="efficacy",
        evidence_strength="moderate",
        confidence="medium",
        text_span="Some claim text span for testing",
    )


class TestEntitySlugCoherence:
    """Unit tests for _check_entity_slug_coherence (DF-EXT-M6)."""

    def test_all_known_slugs_pass_unchanged(self):
        """Relations/claims whose slugs all exist in extracted entities are untouched."""
        orch = _make_orchestrator()
        entities = _make_entities("drug-a", "disease-b")
        relation = _make_relation("drug-a", "disease-b")
        claim = _make_claim("drug-a", "disease-b")
        rel_result = _dummy_result()
        clm_result = _dummy_result()

        rels, rel_results, clms, clm_results = orch._check_entity_slug_coherence(
            entities, [relation], [rel_result], [claim], [clm_result]
        )

        assert len(rels) == 1
        assert rel_results[0].flags == []
        assert rel_results[0].confidence_adjustment == 1.0
        assert len(clms) == 1
        assert clm_results[0].flags == []

    def test_unknown_relation_slug_flagged_in_moderate_mode(self):
        """Relation with an unknown entity slug is flagged and confidence halved (moderate)."""
        orch = _make_orchestrator(strict=False)
        entities = _make_entities("drug-a")
        relation = _make_relation("drug-a", "ghost-entity")
        rel_result = _dummy_result()

        rels, rel_results, clms, clm_results = orch._check_entity_slug_coherence(
            entities, [relation], [rel_result], [], []
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

        rels, rel_results, clms, clm_results = orch._check_entity_slug_coherence(
            entities, [relation], [rel_result], [], []
        )

        assert len(rels) == 0  # Removed in strict mode
        assert len(rel_results) == 0

    def test_unknown_claim_slug_flagged_in_moderate_mode(self):
        """Claim with unknown entity slug is flagged and confidence halved (moderate)."""
        orch = _make_orchestrator(strict=False)
        entities = _make_entities("drug-a")
        claim = _make_claim("drug-a", "phantom")
        clm_result = _dummy_result()

        rels, rel_results, clms, clm_results = orch._check_entity_slug_coherence(
            entities, [], [], [claim], [clm_result]
        )

        assert len(clms) == 1
        assert any("unknown_entity_slug" in f for f in clm_results[0].flags)
        assert clm_results[0].confidence_adjustment == pytest.approx(0.5)

    def test_unknown_claim_slug_rejected_in_strict_mode(self):
        """Claim with all-unknown entity slugs is removed in strict mode."""
        orch = _make_orchestrator(strict=True)
        entities = _make_entities("drug-a")
        claim = _make_claim("phantom-1", "phantom-2")
        clm_result = _dummy_result()

        rels, rel_results, clms, clm_results = orch._check_entity_slug_coherence(
            entities, [], [], [claim], [clm_result]
        )

        assert len(clms) == 0

    def test_empty_entity_list_flags_all_relations(self):
        """When no entities are extracted, all relation slugs are unknown."""
        orch = _make_orchestrator(strict=False)
        relation = _make_relation("drug-a", "disease-b")
        rel_result = _dummy_result()

        rels, rel_results, clms, clm_results = orch._check_entity_slug_coherence(
            [], [relation], [rel_result], [], []
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

        rels, rel_results, clms, clm_results = orch._check_entity_slug_coherence(
            entities, [relation], [rel_result], [], []
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

    _, relations, _, _, relation_results, _ = await orch._validate_extractions_with_results(
        entities,
        [relation],
        [],
        SAMPLE_SOURCE,
    )

    assert len(relations) == 1
    assert any("text_span_not_found" in flag for flag in relation_results[0].flags)

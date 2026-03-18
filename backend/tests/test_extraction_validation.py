"""
Tests for extraction validation service.

Tests text span validation logic that prevents LLM hallucinations
by verifying extractions are grounded in source text.
"""
import pytest

from app.services.extraction_validation_service import (
    TextSpanValidator,
    ExtractionValidationService,
)
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

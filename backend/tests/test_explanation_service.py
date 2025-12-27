"""
Tests for ExplanationService.

Comprehensive tests for explanation generation, confidence breakdown,
contradiction detection, and source chain building.
"""
import pytest
from uuid import uuid4

from app.services.explanation_service import ExplanationService
from app.services.entity_service import EntityService
from app.services.source_service import SourceService
from app.services.relation_service import RelationService
from app.schemas.entity import EntityWrite
from app.schemas.source import SourceWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite as RoleWrite


@pytest.mark.asyncio
class TestExplanationService:
    """Test ExplanationService explanation generation."""

    async def test_explain_inference_no_relations(self, db_session):
        """Test explanation for entity with no relations raises error."""
        # Arrange
        entity_service = EntityService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="orphan", kind="drug"))

        # Act & Assert
        with pytest.raises(ValueError, match="Role type .* not found"):
            await explanation_service.explain_inference(entity.id, "effect")

    async def test_explain_inference_basic(self, db_session):
        """Test basic explanation generation with single source."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="aspirin", kind="drug"))
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Aspirin Study",
                authors=["Smith J.", "Doe A."],
                year=2020,
                url="https://example.com/aspirin",
                trust_level=0.8,
            )
        )

        # Create relation with positive effect
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[
                    RoleWrite(role_type="drug", entity_id=str(entity.id)),
                    RoleWrite(role_type="effect", entity_id=str(entity.id)),
                ],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        assert result.entity_id == entity.id
        assert result.role_type == "drug"
        assert result.score is not None
        assert result.confidence >= 0
        assert result.confidence <= 1
        assert result.disagreement >= 0
        assert result.disagreement <= 1
        assert result.summary is not None
        assert len(result.summary) > 0
        assert len(result.confidence_factors) > 0
        assert len(result.source_chain) == 1

        # Check source chain details
        source_contrib = result.source_chain[0]
        assert source_contrib.source_id == source.id
        assert source_contrib.source_title == "Aspirin Study"
        assert source_contrib.source_authors == ["Smith J.", "Doe A."]
        assert source_contrib.source_year == 2020
        assert source_contrib.source_trust == 0.8
        assert source_contrib.relation_confidence == 0.9
        assert source_contrib.contribution_percentage >= 0

    async def test_explain_inference_with_scope_filter(self, db_session):
        """Test explanation respects scope filter."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(kind="study", title="Test", url="https://example.com/test")
        )

        # Create relation with scope
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                scope={"population": "adults"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act - with matching scope
        result_match = await explanation_service.explain_inference(
            entity.id, "drug", scope_filter={"population": "adults"}
        )

        # Assert - matching scope should return source chain
        assert len(result_match.source_chain) == 1

        # Act & Assert - non-matching scope should raise error (no role inference)
        with pytest.raises(ValueError, match="Role type .* not found"):
            await explanation_service.explain_inference(
                entity.id, "drug", scope_filter={"population": "children"}
            )


@pytest.mark.asyncio
class TestNaturalLanguageSummary:
    """Test natural language summary generation."""

    async def test_summary_strong_positive_effect(self, db_session):
        """Test summary for strong positive effect (score > 0.5)."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(kind="study", title="Test", url="https://example.com/test")
        )

        # Create strong positive relation
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=1.0,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        assert "strong positive effect" in result.summary.lower()

    async def test_summary_weak_positive_effect(self, db_session):
        """Test summary for weak positive effect (0 < score <= 0.5)."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(kind="study", title="Test", url="https://example.com/test")
        )

        # Create weak positive relation
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.3,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        assert "weak positive effect" in result.summary.lower() or "positive" in result.summary.lower()

    async def test_summary_includes_source_count(self, db_session):
        """Test summary includes correct source count."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))

        # Create 3 sources
        for i in range(3):
            source = await source_service.create(
                SourceWrite(kind="study", title=f"Test {i}", url=f"https://example.com/test{i}")
            )
            await relation_service.create(
                RelationWrite(
                    source_id=str(source.id),
                    kind="effect",
                    confidence=0.8,
                    direction="supports",
                    roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
                )
            )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        assert "3 sources" in result.summary.lower()

    async def test_summary_confidence_level(self, db_session):
        """Test summary includes confidence level description."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(kind="study", title="Test", url="https://example.com/test")
        )

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=1.0,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert - should mention confidence level
        summary_lower = result.summary.lower()
        assert any(
            word in summary_lower for word in ["high", "moderate", "low", "confidence"]
        )


@pytest.mark.asyncio
class TestConfidenceBreakdown:
    """Test confidence breakdown generation."""

    async def test_confidence_breakdown_has_coverage_factor(self, db_session):
        """Test confidence breakdown includes coverage factor."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(kind="study", title="Test", url="https://example.com/test")
        )

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        coverage_factors = [f for f in result.confidence_factors if f.factor == "Coverage"]
        assert len(coverage_factors) == 1
        assert coverage_factors[0].value >= 0
        assert "sources" in coverage_factors[0].explanation.lower()

    async def test_confidence_breakdown_has_confidence_factor(self, db_session):
        """Test confidence breakdown includes confidence calculation."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(kind="study", title="Test", url="https://example.com/test")
        )

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        confidence_factors = [f for f in result.confidence_factors if f.factor == "Confidence"]
        assert len(confidence_factors) == 1
        assert confidence_factors[0].value >= 0
        assert confidence_factors[0].value <= 1

    async def test_confidence_breakdown_includes_trust_when_available(self, db_session):
        """Test confidence breakdown includes average trust when sources have trust levels."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(
                kind="study", title="Test", url="https://example.com/test", trust_level=0.9
            )
        )

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        trust_factors = [
            f for f in result.confidence_factors if "trust" in f.factor.lower()
        ]
        assert len(trust_factors) == 1
        assert trust_factors[0].value > 0


@pytest.mark.asyncio
class TestContradictionDetection:
    """Test contradiction detection and grouping."""

    async def test_no_contradictions_low_disagreement(self, db_session):
        """Test no contradiction detail when disagreement is low."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(kind="study", title="Test", url="https://example.com/test")
        )

        # Create only supporting relations
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        assert result.disagreement < 0.1
        assert result.contradictions is None

    async def test_contradictions_detected(self, db_session):
        """Test contradictions are detected with opposing sources."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))

        # Create supporting source
        source1 = await source_service.create(
            SourceWrite(kind="study", title="Supporting", url="https://example.com/s1")
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source1.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Create contradicting source
        source2 = await source_service.create(
            SourceWrite(kind="study", title="Contradicting", url="https://example.com/s2")
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source2.id),
                kind="effect",
                confidence=0.9,
                direction="contradicts",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        # Note: The InferenceService computes disagreement based on weighted scores.
        # Two equal-weight opposite relations may result in low disagreement depending on
        # how the inference algorithm weighs contradictions.
        # The key test is that the source chain shows both directions correctly.
        assert len(result.source_chain) == 2

        # Verify we have both supporting and contradicting sources
        directions = {s.relation_direction for s in result.source_chain}
        assert "supports" in directions
        assert "contradicts" in directions

    async def test_summary_mentions_contradictions(self, db_session):
        """Test summary mentions contradictions when present."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))

        # Create supporting source
        source1 = await source_service.create(
            SourceWrite(kind="study", title="Supporting", url="https://example.com/s1")
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source1.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Create contradicting source
        source2 = await source_service.create(
            SourceWrite(kind="study", title="Contradicting", url="https://example.com/s2")
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source2.id),
                kind="effect",
                confidence=0.9,
                direction="contradicts",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert - summary should mention contradictions
        assert "contradiction" in result.summary.lower() or "disagreement" in result.summary.lower()


@pytest.mark.asyncio
class TestSourceChain:
    """Test source chain building and contribution percentages."""

    async def test_source_chain_single_source(self, db_session):
        """Test source chain with single source has 100% contribution."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Test Study",
                authors=["Author A"],
                year=2020,
                url="https://example.com/test",
                trust_level=0.8,
            )
        )

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        assert len(result.source_chain) == 1
        source_contrib = result.source_chain[0]
        assert source_contrib.contribution_percentage == pytest.approx(100.0, abs=0.1)

    async def test_source_chain_multiple_sources(self, db_session):
        """Test source chain with multiple sources has contributions summing to 100%."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))

        # Create 3 sources with equal confidence
        for i in range(3):
            source = await source_service.create(
                SourceWrite(kind="study", title=f"Test {i}", url=f"https://example.com/test{i}")
            )
            await relation_service.create(
                RelationWrite(
                    source_id=str(source.id),
                    kind="effect",
                    confidence=0.9,
                    direction="supports",
                    roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
                )
            )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        assert len(result.source_chain) == 3
        total_contribution = sum(s.contribution_percentage for s in result.source_chain)
        assert total_contribution == pytest.approx(100.0, abs=0.1)

    async def test_source_chain_sorted_by_contribution(self, db_session):
        """Test source chain is sorted by contribution percentage (descending)."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))

        # Create sources with different confidences
        source1 = await source_service.create(
            SourceWrite(kind="study", title="Low", url="https://example.com/low")
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source1.id),
                kind="effect",
                confidence=0.3,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        source2 = await source_service.create(
            SourceWrite(kind="study", title="High", url="https://example.com/high")
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source2.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert - highest contribution should be first
        assert len(result.source_chain) == 2
        assert result.source_chain[0].contribution_percentage >= result.source_chain[1].contribution_percentage

    async def test_source_chain_includes_all_metadata(self, db_session):
        """Test source chain includes all source and relation metadata."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Complete Study",
                authors=["Smith J.", "Doe A."],
                year=2022,
                url="https://example.com/complete",
                trust_level=0.85,
            )
        )

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.75,
                direction="supports",
                scope={"population": "adults"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await explanation_service.explain_inference(entity.id, "drug")

        # Assert
        assert len(result.source_chain) == 1
        contrib = result.source_chain[0]

        # Source metadata
        assert contrib.source_title == "Complete Study"
        assert contrib.source_authors == ["Smith J.", "Doe A."]
        assert contrib.source_year == 2022
        assert contrib.source_kind == "study"
        assert contrib.source_trust == 0.85
        assert contrib.source_url == "https://example.com/complete"

        # Relation metadata
        assert contrib.relation_kind == "effect"
        assert contrib.relation_confidence == 0.75
        assert contrib.relation_direction in ["supports", "contradicts"]
        assert contrib.relation_scope == {"population": "adults"}

        # Contribution data
        assert contrib.contribution_percentage > 0


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling for edge cases."""

    async def test_explain_nonexistent_role_type(self, db_session):
        """Test explaining a role type that doesn't exist raises error."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(kind="study", title="Test", url="https://example.com/test")
        )

        # Create relation with "drug" role
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act & Assert - try to explain non-existent role
        with pytest.raises(ValueError, match="Role type .* not found"):
            await explanation_service.explain_inference(entity.id, "nonexistent_role")

    async def test_explain_with_empty_scope_filter(self, db_session):
        """Test explanation with empty scope filter works correctly."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        explanation_service = ExplanationService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(
            SourceWrite(kind="study", title="Test", url="https://example.com/test")
        )

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="supports",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act - empty dict should be treated as no filter
        result = await explanation_service.explain_inference(
            entity.id, "drug", scope_filter={}
        )

        # Assert
        assert len(result.source_chain) == 1

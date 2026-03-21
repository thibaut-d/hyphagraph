"""
Tests for year_range calculation in entity filter options.

Tests that year_range is correctly computed from sources with relations.
"""
import pytest

from app.services.entity_service import EntityService
from app.services.source_service import SourceService
from app.services.relation_service import RelationService
from app.schemas.entity import EntityWrite
from app.schemas.source import SourceWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite


@pytest.mark.asyncio
class TestYearRangeCalculation:
    """Test year_range calculation for entity filter options."""

    async def test_year_range_with_relations(self, db_session):
        """Test that year_range reflects sources with relations."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        # Create entities
        entity = await entity_service.create(EntityWrite(slug="test-drug"))
        target = await entity_service.create(EntityWrite(slug="test-condition"))

        # Create sources with different years
        source_1995 = await source_service.create(SourceWrite(
            kind="article",
            title="Old Study",
            year=1995,
            url="https://example.com/1995",
            trust_level=0.8
        ))

        source_2024 = await source_service.create(SourceWrite(
            kind="article",
            title="Recent Study",
            year=2024,
            url="https://example.com/2024",
            trust_level=0.9
        ))

        source_2010 = await source_service.create(SourceWrite(
            kind="article",
            title="Middle Study",
            year=2010,
            url="https://example.com/2010",
            trust_level=0.85
        ))

        # Create relations linking sources to entity
        await relation_service.create(RelationWrite(
            source_id=source_1995.id,
            kind="association",
            direction="supports",
            confidence=0.7,
            roles=[
                RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                RoleRevisionWrite(entity_id=target.id, role_type="target"),
            ]
        ))

        await relation_service.create(RelationWrite(
            source_id=source_2024.id,
            kind="association",
            direction="supports",
            confidence=0.9,
            roles=[
                RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                RoleRevisionWrite(entity_id=target.id, role_type="target"),
            ]
        ))

        await relation_service.create(RelationWrite(
            source_id=source_2010.id,
            kind="association",
            direction="supports",
            confidence=0.8,
            roles=[
                RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                RoleRevisionWrite(entity_id=target.id, role_type="target"),
            ]
        ))

        # Act
        filter_options = await entity_service.get_filter_options()

        # Assert
        assert filter_options.year_range is not None
        min_year, max_year = filter_options.year_range
        assert min_year == 1995
        assert max_year == 2024

    async def test_year_range_empty_database(self, db_session):
        """Test that year_range is None when no sources exist."""
        # Arrange
        entity_service = EntityService(db_session)

        # Act
        filter_options = await entity_service.get_filter_options()

        # Assert
        assert filter_options.year_range is None

    async def test_year_range_ignores_sources_without_relations(self, db_session):
        """Test that year_range only includes sources with relations."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        # Create entities
        entity = await entity_service.create(EntityWrite(slug="test-drug"))
        target = await entity_service.create(EntityWrite(slug="test-condition"))

        # Create a source WITH a relation
        source_with_relation = await source_service.create(SourceWrite(
            kind="article",
            title="Connected Study",
            year=2020,
            url="https://example.com/2020",
            trust_level=0.85
        ))

        # Create a source WITHOUT a relation (orphaned source)
        await source_service.create(SourceWrite(
            title="Orphaned Study",
            year=1990,  # Much older year
            kind="review",
            url="https://example.com/1990",
            trust_level=0.7
        ))

        # Create a source WITHOUT a relation (future source)
        await source_service.create(SourceWrite(
            title="Future Study",
            year=2030,  # Much newer year
            kind="meta_analysis",
            url="https://example.com/2030",
            trust_level=0.9
        ))

        # Only link one source to entity
        await relation_service.create(RelationWrite(
            source_id=source_with_relation.id,
            kind="association",
            direction="supports",
            confidence=0.8,
            roles=[
                RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                RoleRevisionWrite(entity_id=target.id, role_type="target"),
            ]
        ))

        # Act
        filter_options = await entity_service.get_filter_options()

        # Assert
        assert filter_options.year_range is not None
        min_year, max_year = filter_options.year_range
        # Should only reflect the source with a relation (2020)
        # NOT the orphaned sources (1990, 2030)
        assert min_year == 2020
        assert max_year == 2020

    async def test_year_range_with_null_years(self, db_session):
        """Test that year_range handles sources with null years gracefully."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        # Create entities
        entity = await entity_service.create(EntityWrite(slug="test-drug"))
        target = await entity_service.create(EntityWrite(slug="test-condition"))

        # Create sources: some with years, some without
        source_with_year = await source_service.create(SourceWrite(
            kind="article",
            title="Study With Year",
            year=2022,
            url="https://example.com/2022",
            trust_level=0.85
        ))

        source_without_year = await source_service.create(SourceWrite(
            kind="article",
            title="Study Without Year",
            year=None,
            url="https://example.com/no-year",
            trust_level=0.7
        ))

        # Link both sources to entity
        await relation_service.create(RelationWrite(
            source_id=source_with_year.id,
            kind="association",
            direction="supports",
            confidence=0.8,
            roles=[
                RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                RoleRevisionWrite(entity_id=target.id, role_type="target"),
            ]
        ))

        await relation_service.create(RelationWrite(
            source_id=source_without_year.id,
            kind="association",
            direction="supports",
            confidence=0.7,
            roles=[
                RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                RoleRevisionWrite(entity_id=target.id, role_type="target"),
            ]
        ))

        # Act
        filter_options = await entity_service.get_filter_options()

        # Assert
        # Should still return a valid range ignoring null years
        assert filter_options.year_range is not None
        min_year, max_year = filter_options.year_range
        assert min_year == 2022
        assert max_year == 2022

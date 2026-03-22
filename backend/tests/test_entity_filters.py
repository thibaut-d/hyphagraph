"""
Tests for EntityService filtering functionality.

Tests advanced filtering like consensus level, evidence quality, recency, etc.
"""
import pytest

from app.services.entity_service import EntityService
from app.services.source_service import SourceService
from app.services.relation_service import RelationService
from app.schemas.entity import EntityWrite
from app.schemas.source import SourceWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite
from app.schemas.filters import EntityFilters


@pytest.mark.asyncio
class TestEntityConsensusFiltering:
    """Test consensus level filtering for entities."""

    async def test_filter_by_strong_consensus(self, db_session):
        """Test filtering entities with strong consensus (<10% disagreement)."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        # Create an entity
        entity = await entity_service.create(EntityWrite(slug="paracetamol"))
        entity2 = await entity_service.create(EntityWrite(slug="paracetamol-condition"))

        # Create a source
        source = await source_service.create(SourceWrite(
            kind="study",
            title="Study A",
            authors=["Smith, J."],
            year=2020,
            origin="PubMed",
            url="https://example.com/study-a",
            trust_level=0.9
        ))

        # Create 10 relations: 9 "supports", 1 "neutral" = 0% contradicts = strong consensus
        for i in range(9):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="supports",
                confidence=0.8,
                roles=[
                    RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity2.id, role_type="patient")
                ]
            ))

        await relation_service.create(RelationWrite(
            source_id=source.id,
            kind="effect",
            direction="neutral",
            confidence=0.5,
            roles=[
                RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                RoleRevisionWrite(entity_id=entity2.id, role_type="patient")
            ]
        ))

        # Act
        filters = EntityFilters(consensus_level=["strong"])
        items, total = await entity_service.list_all(filters=filters)

        # Assert
        assert total >= 1
        slugs = {item.slug for item in items}
        assert "paracetamol" in slugs

    async def test_filter_by_moderate_consensus(self, db_session):
        """Test filtering entities with moderate consensus (10-30% disagreement)."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        # Create an entity
        entity = await entity_service.create(EntityWrite(slug="aspirin"))
        entity2 = await entity_service.create(EntityWrite(slug="aspirin-condition"))

        # Create a source
        source = await source_service.create(SourceWrite(
            kind="study",
            title="Study B",
            authors=["Doe, A."],
            year=2019,
            origin="PubMed",
            url="https://example.com/study-b",
            trust_level=0.85
        ))

        # Create 10 relations: 7 "supports", 2 "contradicts", 1 "neutral"
        # = 20% contradicts = moderate consensus
        for i in range(7):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="supports",
                confidence=0.7,
                roles=[
                    RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity2.id, role_type="patient"),
                ]
            ))

        for i in range(2):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="contradicts",
                confidence=0.6,
                roles=[
                    RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity2.id, role_type="patient"),
                ]
            ))

        await relation_service.create(RelationWrite(
            source_id=source.id,
            kind="effect",
            direction="neutral",
            confidence=0.5,
            roles=[
                RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                RoleRevisionWrite(entity_id=entity2.id, role_type="patient"),
            ]
        ))

        # Act
        filters = EntityFilters(consensus_level=["moderate"])
        items, total = await entity_service.list_all(filters=filters)

        # Assert
        assert total >= 1
        slugs = {item.slug for item in items}
        assert "aspirin" in slugs

    async def test_filter_by_disputed_consensus(self, db_session):
        """Test filtering entities with disputed consensus (>50% disagreement)."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        # Create an entity
        entity = await entity_service.create(EntityWrite(slug="controversial-drug"))
        entity2 = await entity_service.create(EntityWrite(slug="controversial-condition"))

        # Create a source
        source = await source_service.create(SourceWrite(
            kind="study",
            title="Study C",
            authors=["Johnson, K."],
            year=2021,
            origin="PubMed",
            url="https://example.com/study-c",
            trust_level=0.7
        ))

        # Create 10 relations: 4 "supports", 6 "contradicts"
        # = 60% contradicts = disputed
        for i in range(4):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="supports",
                confidence=0.6,
                roles=[
                    RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity2.id, role_type="patient"),
                ]
            ))

        for i in range(6):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="contradicts",
                confidence=0.7,
                roles=[
                    RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity2.id, role_type="patient"),
                ]
            ))

        # Act
        filters = EntityFilters(consensus_level=["disputed"])
        items, total = await entity_service.list_all(filters=filters)

        # Assert
        assert total >= 1
        slugs = {item.slug for item in items}
        assert "controversial-drug" in slugs

    async def test_filter_by_multiple_consensus_levels(self, db_session):
        """Test filtering by multiple consensus levels (OR logic)."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        # Create entities with different consensus levels
        entity_strong = await entity_service.create(EntityWrite(slug="strong-drug"))
        entity_disputed = await entity_service.create(EntityWrite(slug="disputed-drug"))
        entity_moderate = await entity_service.create(EntityWrite(slug="moderate-drug"))
        entity_condition = await entity_service.create(EntityWrite(slug="shared-condition"))

        source = await source_service.create(SourceWrite(
            kind="study",
            title="Study D",
            authors=["Brown, L."],
            year=2022,
            origin="PubMed",
            url="https://example.com/study-d",
            trust_level=0.8
        ))

        # Strong: 10 supports, 0 contradicts (0%)
        for i in range(10):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="supports",
                confidence=0.8,
                roles=[
                    RoleRevisionWrite(entity_id=entity_strong.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity_condition.id, role_type="patient"),
                ]
            ))

        # Disputed: 4 supports, 6 contradicts (60%)
        for i in range(4):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="supports",
                confidence=0.6,
                roles=[
                    RoleRevisionWrite(entity_id=entity_disputed.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity_condition.id, role_type="patient"),
                ]
            ))
        for i in range(6):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="contradicts",
                confidence=0.7,
                roles=[
                    RoleRevisionWrite(entity_id=entity_disputed.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity_condition.id, role_type="patient"),
                ]
            ))

        # Moderate: 8 supports, 2 contradicts (20%)
        for i in range(8):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="supports",
                confidence=0.75,
                roles=[
                    RoleRevisionWrite(entity_id=entity_moderate.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity_condition.id, role_type="patient"),
                ]
            ))
        for i in range(2):
            await relation_service.create(RelationWrite(
                source_id=source.id,
                kind="effect",
                direction="contradicts",
                confidence=0.6,
                roles=[
                    RoleRevisionWrite(entity_id=entity_moderate.id, role_type="agent"),
                    RoleRevisionWrite(entity_id=entity_condition.id, role_type="patient"),
                ]
            ))

        # Act - Filter for strong OR disputed
        filters = EntityFilters(consensus_level=["strong", "disputed"])
        items, total = await entity_service.list_all(filters=filters)

        # Assert
        assert total == 2
        slugs = {item.slug for item in items}
        assert slugs == {"strong-drug", "disputed-drug"}

    async def test_no_consensus_filter_returns_all(self, db_session):
        """Test that not specifying consensus filter returns all entities."""
        # Arrange
        entity_service = EntityService(db_session)
        await entity_service.create(EntityWrite(slug="drug-a"))
        await entity_service.create(EntityWrite(slug="drug-b"))

        # Act
        filters = EntityFilters()
        items, total = await entity_service.list_all(filters=filters)

        # Assert
        assert total == 2
        slugs = {item.slug for item in items}
        assert slugs == {"drug-a", "drug-b"}

"""
Tests for SourceService.

Tests source CRUD operations with metadata validation.
"""
import pytest
from uuid import uuid4
from fastapi import HTTPException

from app.services.source_service import SourceService
from app.schemas.source import SourceWrite


@pytest.mark.asyncio
class TestSourceService:
    """Test SourceService CRUD operations."""

    async def test_create_source_full(self, db_session):
        """Test creating source with all metadata."""
        # Arrange
        service = SourceService(db_session)
        payload = SourceWrite(
            kind="study",
            title="Aspirin Efficacy Study",
            url="https://example.com/study",
            source_metadata={"doi": "10.1234/test"},
            authors=["Dr. Smith", "Dr. Jones"],
            year=2023,
            origin="PubMed",
            trust_level=8,
            summary={"en": "Clinical trial on aspirin"},
        )

        # Act
        result = await service.create(payload)

        # Assert
        assert result.kind == "study"
        assert result.title == "Aspirin Efficacy Study"
        assert result.url == "https://example.com/study"
        assert result.source_metadata == {"doi": "10.1234/test"}
        assert result.authors == ["Dr. Smith", "Dr. Jones"]
        assert result.year == 2023
        assert result.trust_level == 8
        assert result.id is not None

    async def test_create_source_minimal(self, db_session):
        """Test creating source with only required fields."""
        # Arrange
        service = SourceService(db_session)
        payload = SourceWrite(
            kind="review",
            title="Minimal Source",
            url="https://example.com/minimal",
        )

        # Act
        result = await service.create(payload)

        # Assert
        assert result.kind == "review"
        assert result.title == "Minimal Source"
        assert result.url == "https://example.com/minimal"
        assert result.authors == [] or result.authors is None

    async def test_get_source(self, db_session):
        """Test retrieving an existing source."""
        # Arrange
        service = SourceService(db_session)
        created = await service.create(
            SourceWrite(kind="guideline", title="Test Guideline", url="https://example.com/test"),
            
        )

        # Act
        result = await service.get(created.id)

        # Assert
        assert result.id == created.id
        assert result.title == "Test Guideline"

    async def test_get_source_not_found(self, db_session):
        """Test getting non-existent source raises 404."""
        # Arrange
        service = SourceService(db_session)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.get(uuid4())
        assert exc_info.value.status_code == 404

    async def test_list_all_sources(self, db_session):
        """Test listing all sources."""
        # Arrange
        service = SourceService(db_session)
        await service.create(SourceWrite(kind="study", title="Study 1", url="https://example.com/test"))
        await service.create(SourceWrite(kind="review", title="Review 1", url="https://example.com/test"))

        # Act
        result = await service.list_all()

        # Assert
        assert len(result) >= 2
        titles = {s.title for s in result}
        assert "Study 1" in titles
        assert "Review 1" in titles

    async def test_update_source(self, db_session):
        """Test updating a source."""
        # Arrange
        service = SourceService(db_session)
        created = await service.create(
            SourceWrite(kind="study", title="Original Title", url="https://example.com/test", year=2020)
        )

        # Act
        updated = await service.update(
            created.id,
            SourceWrite(kind="study", title="Updated Title", url="https://example.com/test", year=2023)
        )

        # Assert
        assert updated.id == created.id
        assert updated.title == "Updated Title"
        assert updated.year == 2023

    async def test_update_source_not_found(self, db_session):
        """Test updating non-existent source raises 404."""
        # Arrange
        service = SourceService(db_session)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update(
                uuid4(),
                SourceWrite(kind="study", title="Test", url="https://example.com/test")
            )
        assert exc_info.value.status_code == 404

    async def test_delete_source(self, db_session):
        """Test deleting a source."""
        # Arrange
        service = SourceService(db_session)
        created = await service.create(
            SourceWrite(kind="case_report", title="To Delete", url="https://example.com/test")
        )

        # Act
        await service.delete(created.id)

        # Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.get(created.id)
        assert exc_info.value.status_code == 404

    async def test_delete_source_not_found(self, db_session):
        """Test deleting non-existent source raises 404."""
        # Arrange
        service = SourceService(db_session)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.delete(uuid4())
        assert exc_info.value.status_code == 404

    async def test_list_by_kind(self, db_session):
        """Test filtering sources by kind."""
        # Arrange
        service = SourceService(db_session)
        await service.create(SourceWrite(kind="study", title="Study A", url="https://example.com/test"))
        await service.create(SourceWrite(kind="study", title="Study B", url="https://example.com/test"))
        await service.create(SourceWrite(kind="review", title="Review A", url="https://example.com/test"))

        # Act
        all_sources = await service.list_all()
        studies = [s for s in all_sources if s.kind == "study"]

        # Assert
        assert len(studies) == 2
        assert all(s.kind == "study" for s in studies)

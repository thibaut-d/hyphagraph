"""
Tests for explainability API endpoints.

Tests the /explain/inference/{entity_id}/{role_type} endpoint
including scope filtering, error handling, and response validation.
"""
import pytest
import json
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db
from app.services.entity_service import EntityService
from app.services.source_service import SourceService
from app.services.relation_service import RelationService
from app.schemas.entity import EntityWrite
from fixtures.scientific_data import ScientificEntities, ScientificSources
from app.schemas.source import SourceWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite as RoleWrite


@pytest.fixture
def override_get_db(db_session):
    """Override database dependency with test session."""
    async def _override_get_db():
        yield db_session
    return _override_get_db


@pytest.mark.asyncio
class TestExplainEndpoint:
    """Test /explain/inference/{entity_id}/{role_type} endpoint."""

    async def test_explain_inference_success(self, db_session, override_get_db):
        """Test successful explanation retrieval."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.PREGABALIN["slug"], kind="drug"))
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Aspirin Efficacy Study",
                authors=["Smith J."],
                year=2020,
                url="https://example.com/aspirin",
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
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(f"/api/explain/inference/{entity.id}/drug")
        finally:
            app.dependency_overrides.clear()

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["entity_id"] == str(entity.id)
        assert data["role_type"] == "drug"
        assert "score" in data
        assert "confidence" in data
        assert "disagreement" in data
        assert "summary" in data
        assert "confidence_factors" in data
        assert "source_chain" in data
        assert len(data["source_chain"]) == 1

        # Check source chain structure
        source_contrib = data["source_chain"][0]
        assert source_contrib["source_id"] == str(source.id)
        assert source_contrib["source_title"] == "Aspirin Efficacy Study"
        assert source_contrib["source_authors"] == ["Smith J."]
        assert source_contrib["source_year"] == 2020
        assert source_contrib["relation_confidence"] == 0.9

    async def test_explain_inference_with_scope_filter(self, db_session, override_get_db):
        """Test explanation with scope filter parameter."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
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

        # Act - with matching scope filter
        scope_filter = {"population": "adults"}
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    f"/api/explain/inference/{entity.id}/drug",
                    params={"scope": json.dumps(scope_filter)},
                )
        finally:
            app.dependency_overrides.clear()

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["source_chain"]) == 1
        assert data["scope_filter"] == scope_filter

    async def test_explain_inference_scope_filter_no_match(self, db_session, override_get_db):
        """Test explanation with non-matching scope filter returns 404."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
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

        # Act - with non-matching scope filter
        scope_filter = {"population": "children"}
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    f"/api/explain/inference/{entity.id}/drug",
                    params={"scope": json.dumps(scope_filter)},
                )
        finally:
            app.dependency_overrides.clear()

        # Assert - should return 404 (role not found with that scope)
        assert response.status_code == 404

    async def test_explain_inference_invalid_scope_json(self, db_session, override_get_db):
        """Test explanation with invalid JSON in scope parameter returns 400."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
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

        # Act - with invalid JSON
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    f"/api/explain/inference/{entity.id}/drug",
                    params={"scope": "not-valid-json{"},
                )
        finally:
            app.dependency_overrides.clear()

        # Assert
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["detail"]

    async def test_explain_inference_scope_not_dict(self, db_session, override_get_db):
        """Test explanation with non-dict scope parameter returns 400."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
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

        # Act - with array instead of object
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    f"/api/explain/inference/{entity.id}/drug",
                    params={"scope": json.dumps(["not", "a", "dict"])},
                )
        finally:
            app.dependency_overrides.clear()

        # Assert
        assert response.status_code == 400
        assert "must be a JSON object" in response.json()["detail"]

    async def test_explain_inference_role_not_found(self, db_session, override_get_db):
        """Test explanation for non-existent role type returns 404."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
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

        # Act - request non-existent role
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(f"/api/explain/inference/{entity.id}/nonexistent_role")
        finally:
            app.dependency_overrides.clear()

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_explain_inference_invalid_entity_id(self, override_get_db):
        """Test explanation with invalid entity UUID returns 422."""
        # Act
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/explain/inference/not-a-uuid/drug")
        finally:
            app.dependency_overrides.clear()

        # Assert
        assert response.status_code == 422  # Validation error

    async def test_explain_inference_nonexistent_entity(self, override_get_db):
        """Test explanation for non-existent entity returns 404."""
        # Arrange
        from uuid import uuid4
        fake_entity_id = uuid4()

        # Act
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(f"/api/explain/inference/{fake_entity_id}/drug")
        finally:
            app.dependency_overrides.clear()

        # Assert - should get 404 because role not found
        assert response.status_code == 404

    async def test_explain_inference_multiple_sources(self, db_session, override_get_db):
        """Test explanation with multiple sources returns all contributions."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))

        # Create 3 sources
        for i in range(3):
            source = await source_service.create(
                SourceWrite(
                    kind="study", title=f"Study {i}", url=f"https://example.com/study{i}"
                )
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
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(f"/api/explain/inference/{entity.id}/drug")
        finally:
            app.dependency_overrides.clear()

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["source_chain"]) == 3

        # Verify contributions sum to ~100%
        total_contribution = sum(
            s["contribution_percentage"] for s in data["source_chain"]
        )
        assert abs(total_contribution - 100.0) < 1.0

    async def test_explain_inference_response_structure(self, db_session, override_get_db):
        """Test explanation response has correct structure."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
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
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(f"/api/explain/inference/{entity.id}/drug")
        finally:
            app.dependency_overrides.clear()

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check top-level fields
        required_fields = [
            "entity_id",
            "role_type",
            "score",
            "confidence",
            "disagreement",
            "summary",
            "confidence_factors",
            "source_chain",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Check confidence_factors structure
        assert isinstance(data["confidence_factors"], list)
        if len(data["confidence_factors"]) > 0:
            factor = data["confidence_factors"][0]
            assert "factor" in factor
            assert "value" in factor
            assert "explanation" in factor

        # Check source_chain structure
        assert isinstance(data["source_chain"], list)
        if len(data["source_chain"]) > 0:
            source_contrib = data["source_chain"][0]
            required_source_fields = [
                "source_id",
                "source_title",
                "source_kind",
                "source_url",
                "relation_id",
                "relation_kind",
                "relation_direction",
                "relation_confidence",
                "contribution_percentage",
            ]
            for field in required_source_fields:
                assert field in source_contrib, f"Missing source field: {field}"

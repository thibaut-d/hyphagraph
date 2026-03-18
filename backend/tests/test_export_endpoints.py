from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.service_dependencies import get_export_service, get_typedb_export_service
from app.dependencies.auth import get_current_user
from app.main import app


@pytest.mark.asyncio
async def test_export_entities_uses_export_service_dependency() -> None:
    class StubExportService:
        async def export_entities(self, export_format, include_metadata):
            assert export_format == "json"
            assert include_metadata is True
            return '{"items":[]}'

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="test@example.com")
    app.dependency_overrides[get_export_service] = lambda: StubExportService()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/export/entities")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text == '{"items":[]}'
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_export_sources_json_uses_export_service_dependency() -> None:
    class StubExportService:
        async def export_sources(self, export_format, include_metadata):
            assert export_format == "json"
            assert include_metadata is True
            return '{"export_type":"sources","count":0,"sources":[]}'

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="test@example.com")
    app.dependency_overrides[get_export_service] = lambda: StubExportService()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/export/sources")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == 'attachment; filename="sources.json"'


@pytest.mark.asyncio
async def test_export_sources_csv_uses_export_service_dependency() -> None:
    class StubExportService:
        async def export_sources(self, export_format, include_metadata):
            assert export_format == "csv"
            return "id,kind,title\n"

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="test@example.com")
    app.dependency_overrides[get_export_service] = lambda: StubExportService()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/export/sources?format=csv")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == 'attachment; filename="sources.csv"'


@pytest.mark.asyncio
async def test_export_typedb_full_uses_typedb_service_dependency() -> None:
    class StubTypeDBExportService:
        async def export_full(self):
            return {
                "schema": "define test",
                "data": "insert test",
                "format": "typeql",
                "database": "typedb",
                "version": "3.0",
            }

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="test@example.com")
    app.dependency_overrides[get_typedb_export_service] = lambda: StubTypeDBExportService()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/export/typedb-full")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "schema": "define test",
        "data": "insert test",
        "format": "typeql",
        "database": "typedb",
        "version": "3.0",
    }

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.typedb_export_service import TypeDBExportService, _extract_summary_text


def test_extract_summary_text_uses_english_field_from_dict() -> None:
    assert _extract_summary_text({"en": "English summary", "fr": "Resume"}) == "English summary"


def test_extract_summary_text_falls_back_for_invalid_json_string() -> None:
    invalid_json = '{"en": "Broken"'
    assert _extract_summary_text(invalid_json) == invalid_json


def test_extract_summary_text_falls_back_for_non_dict_json_string() -> None:
    assert _extract_summary_text('["not", "a", "dict"]') == '["not", "a", "dict"]'


@pytest.mark.asyncio
async def test_export_data_handles_invalid_summary_json() -> None:
    entity = SimpleNamespace(id=uuid4())
    revision = SimpleNamespace(slug="duloxetine", summary='{"en": "Broken"')

    entity_result = [(entity, revision)]
    relation_result: list[tuple[object, object, object, object]] = []

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[entity_result, relation_result])

    service = TypeDBExportService(db)

    export = await service.export_data()

    assert 'has slug "duloxetine"' in export
    assert 'has summary "{\\"en\\": \\"Broken\\""' in export


@pytest.mark.asyncio
async def test_export_schema_uses_injected_lookup_services() -> None:
    relation_type_service = AsyncMock()
    relation_type_service.get_all_active.return_value = [
        SimpleNamespace(type_id="treats_condition", description="Treats condition")
    ]
    semantic_role_service = AsyncMock()
    semantic_role_service.get_all_active.return_value = [{"role_type": "target_entity"}]

    service = TypeDBExportService(
        db=AsyncMock(),
        relation_type_service=relation_type_service,
        semantic_role_service=semantic_role_service,
    )

    export = await service.export_schema()

    assert "treats-condition sub relation" in export
    assert "relates target-entity" in export
    relation_type_service.get_all_active.assert_awaited_once()
    semantic_role_service.get_all_active.assert_awaited_once()

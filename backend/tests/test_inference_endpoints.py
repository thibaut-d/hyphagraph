from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.inference_dependencies import get_inference_service
from app.api.service_dependencies import get_entity_service
from app.main import app
from app.schemas.inference import InferenceDetailRead, InferenceRead, InferenceStatsRead


@pytest.mark.asyncio
async def test_inference_endpoints_resolve_slug_ref():
    entity_id = uuid4()
    entity_service = AsyncMock()
    entity_service.resolve_ref_to_id.return_value = entity_id

    inference_service = AsyncMock()
    inference_service.infer_for_entity.return_value = InferenceRead(
        entity_id=entity_id,
        relations_by_kind={},
        role_inferences=[],
    )
    inference_service.get_detail_for_entity.return_value = InferenceDetailRead(
        entity_id=entity_id,
        relations_by_kind={},
        role_inferences=[],
        stats=InferenceStatsRead(
            total_relations=0,
            unique_sources_count=0,
            average_confidence=0.0,
            confidence_count=0,
            high_confidence_count=0,
            low_confidence_count=0,
            contradiction_count=0,
            relation_type_count=0,
        ),
        relation_kind_summaries=[],
        evidence_items=[],
        disagreement_groups=[],
    )

    app.dependency_overrides[get_entity_service] = lambda: entity_service
    app.dependency_overrides[get_inference_service] = lambda: inference_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            inference_response = await client.get("/api/inferences/entity/paracetamol")
            detail_response = await client.get("/api/inferences/entity/paracetamol/detail")
    finally:
        app.dependency_overrides.clear()

    assert inference_response.status_code == 200
    assert inference_response.json()["entity_id"] == str(entity_id)
    assert detail_response.status_code == 200
    assert detail_response.json()["entity_id"] == str(entity_id)
    assert entity_service.resolve_ref_to_id.await_count == 2
    inference_service.infer_for_entity.assert_awaited_once_with(entity_id, scope_filter=None)
    inference_service.get_detail_for_entity.assert_awaited_once_with(entity_id, scope_filter=None)

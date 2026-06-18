from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.inference_dependencies import get_inference_service
from app.api.service_dependencies import get_entity_service
from app.dependencies.auth import get_current_user
from app.main import app
from app.schemas.entity import EntityRead
from app.schemas.inference import InferenceDetailRead, InferenceRead, InferenceStatsRead


class FakeLLMProvider:
    async def generate_json(
        self,
        prompt,
        system_prompt=None,
        temperature=None,
        max_tokens=2000,
        **kwargs,
    ):
        return {
            "synthesis": "A concise synthesis of the computed relationships.",
            "key_points": ["Evidence mostly supports the main relation."],
            "limitations": ["Coverage is limited."],
            "evidence_note": "Generated from computed graph relationships.",
            "general_knowledge_note": "General background was kept separate.",
        }

    def get_model_name(self):
        return "fake-synthesis-model"


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


@pytest.mark.asyncio
async def test_ai_synthesis_endpoint_generates_only_on_post(monkeypatch):
    entity_id = uuid4()
    user_id = uuid4()
    entity = EntityRead(
        id=entity_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        slug="paracetamol",
        status="confirmed",
        summary={"en": "Analgesic medication."},
    )

    entity_service = AsyncMock()
    entity_service.get_by_ref.return_value = entity

    inference_service = AsyncMock()
    inference_service.get_detail_for_entity.return_value = InferenceDetailRead(
        entity_id=entity_id,
        relations_by_kind={},
        role_inferences=[],
        stats=InferenceStatsRead(
            total_relations=2,
            unique_sources_count=1,
            average_confidence=0.6,
            confidence_count=2,
            high_confidence_count=1,
            low_confidence_count=0,
            contradiction_count=0,
            relation_type_count=1,
        ),
        relation_kind_summaries=[],
        evidence_items=[],
        disagreement_groups=[],
    )

    monkeypatch.setattr("app.api.inferences.is_llm_available", lambda: True)
    monkeypatch.setattr("app.api.inferences.get_llm_provider", lambda: FakeLLMProvider())
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    app.dependency_overrides[get_entity_service] = lambda: entity_service
    app.dependency_overrides[get_inference_service] = lambda: inference_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/inferences/entity/paracetamol/ai-synthesis",
                json={
                    "user_language": "en",
                    "scope_filter": {"population": "adults"},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["entity_id"] == str(entity_id)
    assert body["entity_slug"] == "paracetamol"
    assert body["synthesis"] == "A concise synthesis of the computed relationships."
    assert body["generated_with_llm"] == "fake-synthesis-model"
    assert body["source_relation_count"] == 2
    entity_service.get_by_ref.assert_awaited_once_with("paracetamol")
    inference_service.get_detail_for_entity.assert_awaited_once_with(
        entity_id,
        scope_filter={"population": "adults"},
    )

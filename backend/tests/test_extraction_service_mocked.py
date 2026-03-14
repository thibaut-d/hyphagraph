from unittest.mock import AsyncMock

import pytest

from app.services.extraction_service import ExtractionService


@pytest.mark.asyncio
async def test_extraction_service_uses_injected_prompt_services() -> None:
    relation_type_service = AsyncMock()
    relation_type_service.get_for_llm_prompt.return_value = "RELATION PROMPT"
    semantic_role_service = AsyncMock()
    semantic_role_service.get_for_llm_prompt.return_value = "ROLE PROMPT"

    service = ExtractionService(
        db=AsyncMock(),
        relation_type_service=relation_type_service,
        semantic_role_service=semantic_role_service,
    )

    relation_prompt = await service._get_relation_types_prompt()
    semantic_prompt = await service._get_semantic_roles_prompt()

    assert relation_prompt == "RELATION PROMPT"
    assert semantic_prompt == "ROLE PROMPT"
    relation_type_service.get_for_llm_prompt.assert_awaited_once()
    semantic_role_service.get_for_llm_prompt.assert_awaited_once()

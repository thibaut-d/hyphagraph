from unittest.mock import AsyncMock, MagicMock, patch

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


@pytest.mark.asyncio
async def test_extraction_status_uses_provider_model_name() -> None:
    """extraction_status returns model name from provider.get_model_name() (DF-EXT-M7)."""
    from app.api.extraction import extraction_status

    mock_provider = MagicMock()
    mock_provider.get_model_name.return_value = "gpt-4o"

    with patch("app.api.extraction.is_llm_available", return_value=True), \
         patch("app.api.extraction.get_llm_provider", return_value=mock_provider):
        result = await extraction_status()

    assert result.available is True
    assert result.model == "gpt-4o"
    mock_provider.get_model_name.assert_called_once()


@pytest.mark.asyncio
async def test_extraction_status_unavailable_returns_none_model() -> None:
    """extraction_status returns model=None when LLM is not configured (DF-EXT-M7)."""
    from app.api.extraction import extraction_status

    with patch("app.api.extraction.is_llm_available", return_value=False):
        result = await extraction_status()

    assert result.available is False
    assert result.model is None
    assert result.provider is None

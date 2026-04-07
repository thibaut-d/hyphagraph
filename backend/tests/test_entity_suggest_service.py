from unittest.mock import AsyncMock

import pytest

from app.llm.base import LLMError
from app.services.entity_suggest_service import EntitySuggestService
from app.utils.errors import AppException


def _make_service(llm_return_value=None, llm_side_effect=None):
    llm_provider = AsyncMock()
    if llm_side_effect is not None:
        llm_provider.generate_json.side_effect = llm_side_effect
    else:
        llm_provider.generate_json.return_value = llm_return_value
    return EntitySuggestService(llm_provider=llm_provider), llm_provider


@pytest.mark.asyncio
async def test_suggest_returns_cleaned_terms() -> None:
    service, llm = _make_service(
        llm_return_value={"terms": ["Morphine", "Codeine", "Tramadol"]}
    )
    result = await service.suggest_entity_terms(
        query="opioid pain medication", count=3, user_language="en"
    )
    assert result == ["Morphine", "Codeine", "Tramadol"]
    llm.generate_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_suggest_prompt_contains_query_and_count() -> None:
    service, llm = _make_service(
        llm_return_value={"terms": ["Aspirin", "Ibuprofen"]}
    )
    await service.suggest_entity_terms(
        query="anti-inflammatory drugs", count=2, user_language="en"
    )
    call_kwargs = llm.generate_json.await_args.kwargs
    assert "anti-inflammatory drugs" in call_kwargs["prompt"]
    assert "2" in call_kwargs["prompt"]
    assert call_kwargs["temperature"] == 0
    assert call_kwargs["max_tokens"] == 800


@pytest.mark.asyncio
async def test_suggest_caps_result_at_count() -> None:
    # LLM returns more than requested
    service, _ = _make_service(
        llm_return_value={"terms": ["A", "B", "C", "D", "E"]}
    )
    result = await service.suggest_entity_terms(
        query="some topic", count=3, user_language="en"
    )
    assert result == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_suggest_deduplicates_case_insensitively() -> None:
    service, _ = _make_service(
        llm_return_value={"terms": ["morphine", "Morphine", "MORPHINE", "Codeine"]}
    )
    result = await service.suggest_entity_terms(
        query="opioids", count=10, user_language="en"
    )
    assert result == ["morphine", "Codeine"]


@pytest.mark.asyncio
async def test_suggest_strips_whitespace_from_terms() -> None:
    service, _ = _make_service(
        llm_return_value={"terms": ["  Aspirin  ", "\nIbuprofen\n", ""]}
    )
    result = await service.suggest_entity_terms(
        query="nsaids", count=10, user_language="en"
    )
    assert result == ["Aspirin", "Ibuprofen"]


@pytest.mark.asyncio
async def test_suggest_skips_non_string_items() -> None:
    service, _ = _make_service(
        llm_return_value={"terms": ["Aspirin", 42, None, True, "Ibuprofen"]}
    )
    result = await service.suggest_entity_terms(
        query="nsaids", count=10, user_language="en"
    )
    assert result == ["Aspirin", "Ibuprofen"]


@pytest.mark.asyncio
async def test_suggest_llm_error_raises_app_exception() -> None:
    service, _ = _make_service(llm_side_effect=LLMError("provider down"))
    with pytest.raises(AppException) as exc_info:
        await service.suggest_entity_terms(
            query="chronic pain", count=5, user_language="en"
        )
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_suggest_missing_terms_key_raises_app_exception() -> None:
    service, _ = _make_service(llm_return_value={"suggestions": ["Aspirin"]})
    with pytest.raises(AppException) as exc_info:
        await service.suggest_entity_terms(
            query="chronic pain", count=5, user_language="en"
        )
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_suggest_non_list_terms_raises_app_exception() -> None:
    service, _ = _make_service(llm_return_value={"terms": "not a list"})
    with pytest.raises(AppException) as exc_info:
        await service.suggest_entity_terms(
            query="chronic pain", count=5, user_language="en"
        )
    assert exc_info.value.status_code == 502

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.llm.openai_provider import OpenAIProvider


def _build_openai_response() -> SimpleNamespace:
    return SimpleNamespace(
        id="resp_123",
        created=1234567890,
        model="test-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="ok"),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
    )


def _build_provider(model: str) -> tuple[OpenAIProvider, AsyncMock]:
    provider = OpenAIProvider(api_key="test-key", model=model, temperature=0.0)
    create_mock = AsyncMock(return_value=_build_openai_response())
    provider.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create_mock)
        )
    )
    return provider, create_mock


@pytest.mark.asyncio
async def test_generate_uses_max_completion_tokens_for_gpt5_models() -> None:
    provider, create_mock = _build_provider("gpt-5.4")

    await provider.generate("hello", max_tokens=321)

    kwargs = create_mock.await_args.kwargs
    assert kwargs["max_completion_tokens"] == 321
    assert "max_tokens" not in kwargs


@pytest.mark.asyncio
async def test_generate_uses_max_tokens_for_legacy_models() -> None:
    provider, create_mock = _build_provider("gpt-4o")

    await provider.generate("hello", max_tokens=123)

    kwargs = create_mock.await_args.kwargs
    assert kwargs["max_tokens"] == 123
    assert "max_completion_tokens" not in kwargs


@pytest.mark.asyncio
async def test_generate_respects_explicit_token_param_override() -> None:
    provider, create_mock = _build_provider("gpt-5.4")

    await provider.generate("hello", max_tokens=321, max_completion_tokens=99)

    kwargs = create_mock.await_args.kwargs
    assert kwargs["max_completion_tokens"] == 99
    assert "max_tokens" not in kwargs

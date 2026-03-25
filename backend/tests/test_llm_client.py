"""
Tests for the LLM provider singleton in app/llm/client.py.

Covers: key-rotation invalidation, reset_llm_provider(), and the
RuntimeError raised when no key is configured.
"""
from unittest.mock import patch

import pytest

import app.llm.client as llm_client
from app.llm.client import get_llm_provider, reset_llm_provider
from app.llm.openai_provider import OpenAIProvider


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure the singleton is clean before and after every test."""
    reset_llm_provider()
    yield
    reset_llm_provider()


class TestGetLlmProvider:
    def test_returns_openai_provider_when_key_set(self):
        with patch.object(llm_client.settings, "OPENAI_API_KEY", "key-abc"):
            provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)

    def test_returns_same_instance_on_repeated_calls(self):
        with patch.object(llm_client.settings, "OPENAI_API_KEY", "key-abc"):
            p1 = get_llm_provider()
            p2 = get_llm_provider()
        assert p1 is p2

    def test_raises_when_no_key_configured(self):
        with patch.object(llm_client.settings, "OPENAI_API_KEY", None):
            with pytest.raises(RuntimeError, match="No LLM provider configured"):
                get_llm_provider()

    def test_reinitialises_on_key_rotation(self):
        with patch.object(llm_client.settings, "OPENAI_API_KEY", "key-old"):
            p1 = get_llm_provider()

        with patch.object(llm_client.settings, "OPENAI_API_KEY", "key-new"):
            p2 = get_llm_provider()

        assert p1 is not p2

    def test_same_key_does_not_reinitialise(self):
        with patch.object(llm_client.settings, "OPENAI_API_KEY", "key-same"):
            p1 = get_llm_provider()
            p2 = get_llm_provider()
        assert p1 is p2


class TestResetLlmProvider:
    def test_reset_forces_new_instance(self):
        with patch.object(llm_client.settings, "OPENAI_API_KEY", "key-abc"):
            p1 = get_llm_provider()
            reset_llm_provider()
            p2 = get_llm_provider()
        assert p1 is not p2

    def test_reset_is_idempotent(self):
        reset_llm_provider()
        reset_llm_provider()  # no error
        with patch.object(llm_client.settings, "OPENAI_API_KEY", "key-abc"):
            provider = get_llm_provider()
        assert provider is not None

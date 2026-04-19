"""
LLM client singleton for application-wide access.

Provides a convenient way to access the configured LLM provider
throughout the application.
"""
import logging

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

# Singleton instances and the keys they were built with.
_llm_provider: LLMProvider | None = None
_llm_provider_key: str | None = None

_prefill_llm_provider: LLMProvider | None = None
_prefill_llm_provider_key: str | None = None


def get_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider instance.

    Returns a singleton instance of the LLM provider based on configuration.
    The singleton is automatically invalidated when OPENAI_API_KEY changes so
    that a key rotation takes effect without a process restart.

    Returns:
        LLMProvider instance

    Raises:
        RuntimeError: If no LLM provider is configured
    """
    global _llm_provider, _llm_provider_key

    current_key = settings.OPENAI_API_KEY

    # Reinitialise if the key has been rotated since the singleton was created.
    if _llm_provider is not None and _llm_provider_key != current_key:
        logger.info("OPENAI_API_KEY changed — reinitialising LLM provider")
        _llm_provider = None
        _llm_provider_key = None

    if _llm_provider is None:
        if current_key:
            logger.info("Initializing OpenAI LLM provider")
            _llm_provider = OpenAIProvider()
            _llm_provider_key = current_key
        else:
            raise RuntimeError(
                "No LLM provider configured. Please set OPENAI_API_KEY in .env"
            )

    return _llm_provider


def get_prefill_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider for entity prefill and suggest tasks.

    Uses OPENAI_PREFILL_MODEL (a lighter/faster model) instead of the main
    extraction model. Singleton follows the same key-rotation semantics as
    get_llm_provider().

    Returns:
        LLMProvider instance configured for the prefill model

    Raises:
        RuntimeError: If no LLM provider is configured
    """
    global _prefill_llm_provider, _prefill_llm_provider_key

    current_key = settings.OPENAI_API_KEY

    if _prefill_llm_provider is not None and _prefill_llm_provider_key != current_key:
        logger.info("OPENAI_API_KEY changed — reinitialising prefill LLM provider")
        _prefill_llm_provider = None
        _prefill_llm_provider_key = None

    if _prefill_llm_provider is None:
        if current_key:
            logger.info("Initializing OpenAI prefill LLM provider (model=%s)", settings.OPENAI_PREFILL_MODEL)
            _prefill_llm_provider = OpenAIProvider(model=settings.OPENAI_PREFILL_MODEL)
            _prefill_llm_provider_key = current_key
        else:
            raise RuntimeError(
                "No LLM provider configured. Please set OPENAI_API_KEY in .env"
            )

    return _prefill_llm_provider


def reset_llm_provider() -> None:
    """Reset the LLM provider singleton.

    Forces the next call to get_llm_provider() to create a fresh instance.
    Intended for use in tests and after runtime configuration changes.
    """
    global _llm_provider, _llm_provider_key
    _llm_provider = None
    _llm_provider_key = None


def reset_prefill_llm_provider() -> None:
    """Reset the prefill LLM provider singleton.

    Forces the next call to get_prefill_llm_provider() to create a fresh instance.
    Intended for use in tests and after runtime configuration changes.
    """
    global _prefill_llm_provider, _prefill_llm_provider_key
    _prefill_llm_provider = None
    _prefill_llm_provider_key = None


def is_llm_available() -> bool:
    """
    Check if any LLM provider is available.

    Returns:
        True if an LLM provider is configured and available
    """
    try:
        provider = get_llm_provider()
        return provider.is_available()
    except RuntimeError:
        return False


# Convenience alias
llm = get_llm_provider

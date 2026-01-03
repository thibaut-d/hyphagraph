"""
LLM client singleton for application-wide access.

Provides a convenient way to access the configured LLM provider
throughout the application.
"""
import logging
from typing import cast

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

# Singleton instance
_llm_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider instance.

    Returns a singleton instance of the LLM provider based on configuration.
    Currently only supports OpenAI, but can be extended for other providers.

    Returns:
        LLMProvider instance

    Raises:
        RuntimeError: If no LLM provider is configured
    """
    global _llm_provider

    if _llm_provider is None:
        # Try to initialize OpenAI provider
        if settings.OPENAI_API_KEY:
            logger.info("Initializing OpenAI LLM provider")
            _llm_provider = OpenAIProvider()
        else:
            raise RuntimeError(
                "No LLM provider configured. Please set OPENAI_API_KEY in .env"
            )

    return _llm_provider


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

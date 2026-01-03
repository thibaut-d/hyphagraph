"""
LLM integration module for HyphaGraph.

Provides abstract interface and implementations for various LLM providers
to enable knowledge extraction from documents.
"""
from app.llm.base import LLMProvider, LLMResponse, LLMError
from app.llm.openai_provider import OpenAIProvider
from app.llm.client import get_llm_provider, is_llm_available, llm

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMError",
    "OpenAIProvider",
    "get_llm_provider",
    "is_llm_available",
    "llm",
]

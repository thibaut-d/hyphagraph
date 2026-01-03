"""
Base abstract interface for LLM providers.

Defines the contract that all LLM provider implementations must follow.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


@dataclass
class LLMResponse:
    """
    Standardized response from LLM providers.

    Attributes:
        content: The generated text response
        model: The model that generated the response
        usage: Token usage information (prompt_tokens, completion_tokens, total_tokens)
        metadata: Additional provider-specific metadata
    """
    content: str
    model: str
    usage: dict[str, int]
    metadata: dict[str, Any] | None = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM provider implementations (OpenAI, Anthropic, Google, etc.)
    must inherit from this class and implement the required methods.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            prompt: The user prompt/query
            system_prompt: Optional system prompt to set context/behavior
            temperature: Sampling temperature (0.0-1.0, lower = more deterministic)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse containing the generated text and metadata

        Raises:
            LLMError: If the API call fails or returns an error
        """
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a structured JSON response from the LLM.

        Uses JSON mode or function calling to ensure the response is valid JSON.

        Args:
            prompt: The user prompt/query
            system_prompt: Optional system prompt to set context/behavior
            temperature: Sampling temperature (0.0-1.0, lower = more deterministic)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Parsed JSON response as a Python dictionary

        Raises:
            LLMError: If the API call fails or returns invalid JSON
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available (API key configured, etc.).

        Returns:
            True if the provider can be used, False otherwise
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name/identifier of the model being used.

        Returns:
            Model name (e.g., "gpt-4o-mini", "claude-3-sonnet")
        """
        pass

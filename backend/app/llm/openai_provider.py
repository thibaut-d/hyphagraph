"""
OpenAI provider implementation for ChatGPT.

Provides integration with OpenAI's Chat Completions API.
"""
import json
import logging
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from app.config import settings
from app.llm.base import LLMProvider, LLMResponse, LLMError

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """
    OpenAI ChatGPT provider implementation.

    Supports GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, and other OpenAI models.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (defaults to settings.OPENAI_API_KEY)
            model: Model to use (defaults to settings.OPENAI_MODEL)
            temperature: Default temperature (defaults to settings.OPENAI_TEMPERATURE)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.default_temperature = temperature or settings.OPENAI_TEMPERATURE

        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)

    def is_available(self) -> bool:
        """Check if OpenAI provider is available."""
        return self.client is not None and self.api_key is not None

    def get_model_name(self) -> str:
        """Get the configured model name."""
        return self.model

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a completion using OpenAI Chat Completions API.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (uses default if not specified)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI API parameters

        Returns:
            LLMResponse with generated content

        Raises:
            LLMError: If API call fails or provider not available
        """
        if not self.is_available():
            raise LLMError("OpenAI provider not available - API key not configured")

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Use default temperature if not specified
        temp = temperature if temperature is not None else self.default_temperature

        try:
            logger.info(f"Calling OpenAI API with model={self.model}, temp={temp}")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tokens,
                **kwargs,
            )

            # Extract content
            content = response.choices[0].message.content or ""

            # Build usage dict
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            # Build metadata
            metadata = {
                "finish_reason": response.choices[0].finish_reason,
                "id": response.id,
                "created": response.created,
            }

            logger.info(f"OpenAI response: {usage['total_tokens']} tokens used")

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                metadata=metadata,
            )

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMError(f"OpenAI API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {e}")
            raise LLMError(f"Unexpected error: {str(e)}") from e

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a structured JSON response using OpenAI's JSON mode.

        Args:
            prompt: User prompt (should instruct to respond with JSON)
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI API parameters

        Returns:
            Parsed JSON as a Python dictionary

        Raises:
            LLMError: If API call fails or response is not valid JSON
        """
        if not self.is_available():
            raise LLMError("OpenAI provider not available - API key not configured")

        # Ensure JSON mode is requested
        kwargs["response_format"] = {"type": "json_object"}

        # Add JSON instruction to system prompt if not present
        json_instruction = "You must respond with valid JSON only. Do not include any text outside the JSON object."
        if system_prompt:
            system_prompt = f"{system_prompt}\n\n{json_instruction}"
        else:
            system_prompt = json_instruction

        # Generate response
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Parse JSON
        try:
            result = json.loads(response.content)
            logger.info(f"Successfully parsed JSON response from OpenAI")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from OpenAI response: {e}")
            logger.error(f"Response content: {response.content[:500]}")
            raise LLMError(f"Invalid JSON in response: {str(e)}") from e

"""
OpenAI provider implementation for ChatGPT.

Provides integration with OpenAI's Chat Completions API.
"""
import json
import logging

from openai import AsyncOpenAI, OpenAIError

from app.config import settings
from app.llm.base import LLMProvider, LLMResponse, LLMError
from app.schemas.common_types import JsonObject, JsonValue

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
        self.default_temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE

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

    def _get_token_limit_param_name(self) -> str:
        """
        Return the token-limit parameter accepted by the configured model.

        GPT-5 chat-completions models reject `max_tokens` and require
        `max_completion_tokens`. Keep the provider interface stable and translate
        here so upstream extraction code does not need model-specific branching.
        """
        normalized_model = (self.model or "").strip().lower()
        return "max_completion_tokens" if normalized_model.startswith("gpt-5") else "max_tokens"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 2000,
        **kwargs: JsonValue,
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

            request_kwargs = dict(kwargs)
            if (
                "max_tokens" not in request_kwargs
                and "max_completion_tokens" not in request_kwargs
            ):
                request_kwargs[self._get_token_limit_param_name()] = max_tokens

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                **request_kwargs,
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
            logger.exception("OpenAI API error")
            raise LLMError("OpenAI API call failed") from e
        except Exception as e:
            logger.exception("Unexpected error calling OpenAI")
            raise LLMError("Unexpected LLM provider error") from e

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 2000,
        **kwargs: JsonValue,
    ) -> JsonObject:
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
            if not isinstance(result, dict):
                raise LLMError("Invalid JSON in response: expected a JSON object")
            logger.info(f"Successfully parsed JSON response from OpenAI")
            return result
        except json.JSONDecodeError as e:
            logger.exception("Failed to parse JSON from OpenAI response")
            logger.error("Response content (first 500 chars): %s", response.content[:500])
            raise LLMError("LLM response could not be parsed as JSON") from e

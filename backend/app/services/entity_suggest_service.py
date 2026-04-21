from __future__ import annotations

import logging

from app.llm.base import LLMError, LLMProvider
from app.utils.errors import AppException, ErrorCode, ValidationException

logger = logging.getLogger(__name__)


class EntitySuggestService:
    """Suggest entity term names for a free-text topic query using an LLM.

    The output is non-authoritative — it is presented to the user for review
    before any entities are created.
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def suggest_entity_terms(
        self,
        query: str,
        count: int,
        user_language: str,
    ) -> list[str]:
        """Return up to `count` distinct entity name suggestions for `query`.

        Terms are canonical English or internationally used names (generic /
        INN names for medicines — never brand names).  The list is deduped
        case-insensitively and capped at `count`.
        """
        normalized_query = query.strip()
        if not normalized_query:
            raise ValidationException("Query is required", field="query")

        raw_terms = await self._call_llm(normalized_query, count, user_language)
        return self._clean_terms(raw_terms, count)

    async def _call_llm(self, query: str, count: int, user_language: str) -> list[object]:
        system_prompt = (
            "You suggest entity names for a scientific knowledge graph. "
            "Suggestions are non-authoritative proposals for human review. "
            "Return only JSON matching the requested shape — no prose, no markdown."
        )
        prompt = (
            f"Suggest {count} entity names related to this topic: {query}\n"
            f"User interface language: {user_language}\n\n"
            f"Return a JSON object with exactly one field:\n"
            f"- terms: array of exactly {count} entity name strings\n\n"
            "Rules:\n"
            "- Each term must be the canonical English or internationally used name for the entity.\n"
            "- For medicines and drugs, always use the generic or INN (International Nonproprietary Name) — never a brand name.\n"
            "- Each term should name a distinct, well-defined concept (substance, condition, intervention, organism, etc.).\n"
            "- Prefer terms at the right level of specificity for a scientific knowledge graph — not too broad, not too narrow.\n"
            "- Do not repeat the same concept under different names.\n"
            "- Do not include relation statements, efficacy statements, or any other text — only the entity names.\n"
            f"- Return exactly {count} terms.\n"
        )
        try:
            data = await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0,
                max_tokens=800,
            )
        except LLMError as exc:
            raise AppException(
                status_code=502,
                error_code=ErrorCode.LLM_API_ERROR,
                message="AI suggestion failed",
                details="The LLM provider failed while generating entity suggestions.",
            ) from exc

        terms = data.get("terms")
        if not isinstance(terms, list):
            logger.warning(
                "Entity suggest LLM response missing 'terms' list: %r", data
            )
            raise AppException(
                status_code=502,
                error_code=ErrorCode.LLM_API_ERROR,
                message="AI suggestion returned an unexpected format",
                details="Expected a JSON object with a 'terms' array.",
            )
        return terms

    def _clean_terms(self, raw: list[object], count: int) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in raw:
            if not isinstance(item, str):
                continue
            term = item.strip()
            if not term:
                continue
            key = term.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(term)
            if len(result) >= count:
                break
        return result

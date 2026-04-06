import json
import logging
import re
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMError, LLMProvider
from app.models.ui_category import UiCategory
from app.schemas.entity import EntityPrefillAlias, EntityPrefillDraft
from app.utils.errors import AppException, ErrorCode, ValidationException

logger = logging.getLogger(__name__)

_LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}$")


class EntityPrefillService:
    """Build non-authoritative create-entity drafts with an LLM."""

    def __init__(self, db: AsyncSession, llm_provider: LLMProvider):
        self.db = db
        self.llm_provider = llm_provider

    async def generate_draft(self, term: str, user_language: str) -> EntityPrefillDraft:
        normalized_term = term.strip()
        normalized_language = user_language.strip().lower()
        if not normalized_term:
            raise ValidationException("Term is required", field="term")
        if not _LANGUAGE_PATTERN.fullmatch(normalized_language):
            raise ValidationException("Invalid user language", field="user_language")

        category_prompt = await self._build_category_prompt()
        response_data = await self._call_llm(normalized_term, normalized_language, category_prompt)
        return self._validate_response(response_data)

    async def _build_category_prompt(self) -> str:
        result = await self.db.execute(select(UiCategory).order_by(UiCategory.sort_order, UiCategory.id))
        categories = result.scalars().all()
        if not categories:
            return "No UI categories are available. Return null for ui_category_id."

        lines = []
        for category in categories:
            lines.append(f"- id: {category.id}; label: {json.dumps(category.label, ensure_ascii=False)}")
        return "Allowed UI categories:\n" + "\n".join(lines)

    async def _call_llm(
        self,
        term: str,
        user_language: str,
        category_prompt: str,
    ) -> dict[str, object]:
        system_prompt = (
            "You draft editable metadata for a knowledge-graph entity creation form. "
            "The draft is not authoritative. Do not invent factual claims. "
            "If you are uncertain about a summary, return an empty summary object. "
            "Return only JSON matching the requested shape."
        )
        prompt = f"""
Draft values for a new entity from this user term: {term}
User interface language: {user_language}

{category_prompt}

Return a JSON object with exactly these fields:
- slug: lowercase URL slug, 3-100 chars, matching ^[a-z][a-z0-9-]*$
- display_names: object mapping language code to display name; use "" for international/no language
- summary: object mapping language code to short neutral summary text
- aliases: array of objects with term and language; language may be null for international/no language
- ui_category_id: one allowed category id string or null

Rules:
- Prefer an international display name when the term is internationally used.
- If the term is language-specific, put it under the user interface language.
- Include aliases only when they are common names or translations, not speculative.
- Do not include relation claims, treatment claims, efficacy claims, or confidence language.
"""
        try:
            return await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0,
                max_tokens=1200,
            )
        except LLMError as exc:
            raise AppException(
                status_code=502,
                error_code=ErrorCode.LLM_API_ERROR,
                message="AI draft generation failed",
                details="The LLM provider failed while generating entity draft values.",
            ) from exc

    def _validate_response(self, response_data: dict[str, object]) -> EntityPrefillDraft:
        allowed_categories: set[UUID] = set()
        if "ui_category_id" in response_data and response_data["ui_category_id"]:
            try:
                allowed_categories.add(UUID(str(response_data["ui_category_id"])))
            except ValueError as exc:
                raise ValidationException(
                    "AI draft returned an invalid category",
                    field="ui_category_id",
                ) from exc

        try:
            draft = EntityPrefillDraft.model_validate(response_data)
        except ValidationError as exc:
            logger.warning("Entity prefill LLM response failed validation: %s", exc)
            raise ValidationException(
                "AI draft could not be used",
                details="The LLM returned draft values that failed validation.",
            ) from exc

        return EntityPrefillDraft(
            slug=draft.slug,
            display_names=self._clean_language_map(draft.display_names),
            summary=self._clean_language_map(draft.summary, allow_international=False),
            aliases=self._clean_aliases(draft.aliases),
            ui_category_id=draft.ui_category_id if draft.ui_category_id in allowed_categories else None,
        )

    def _clean_language_map(
        self,
        values: dict[str, str],
        allow_international: bool = True,
    ) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for language, value in values.items():
            normalized_language = language.strip().lower()
            if normalized_language == "international":
                normalized_language = ""
            if normalized_language and not _LANGUAGE_PATTERN.fullmatch(normalized_language):
                continue
            if normalized_language == "" and not allow_international:
                continue
            normalized_value = value.strip()
            if normalized_value:
                cleaned[normalized_language] = normalized_value
        return cleaned

    def _clean_aliases(self, aliases: list[EntityPrefillAlias]) -> list[EntityPrefillAlias]:
        cleaned: list[EntityPrefillAlias] = []
        seen: set[tuple[str, str | None]] = set()
        for alias in aliases:
            language = alias.language.strip().lower() if alias.language else None
            term = alias.term.strip()
            if not term:
                continue
            key = (term.casefold(), language)
            if key in seen:
                continue
            cleaned.append(EntityPrefillAlias(term=term, language=language))
            seen.add(key)
        return cleaned

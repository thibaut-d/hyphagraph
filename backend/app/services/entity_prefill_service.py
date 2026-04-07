import json
import logging
import re
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMError, LLMProvider
from app.llm.schemas import ExtractedEntity
from app.models.ui_category import UiCategory
from app.schemas.entity import EntityPrefillAlias, EntityPrefillDraft
from app.utils.errors import AppException, ErrorCode, ValidationException

logger = logging.getLogger(__name__)

_LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}$")
_ACRONYM_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,14}[A-Z0-9]$")
_DOSAGE_OR_STRENGTH_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mcg|μg|mg|g|kg|ml|mL|l|L|iu|ui|%)\b",
    re.IGNORECASE,
)
_ENGLISH_ALIAS_QUALIFIER_PATTERN = re.compile(
    r"\b(syndrome|disease|condition|disorder|salt|formulation|class|tablet|tablets|capsule|capsules)\b",
    re.IGNORECASE,
)
_PREFILL_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("fr", "French"),
    ("es", "Spanish"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("la", "Latin"),
)
_PREFILL_LANGUAGE_LABELS = dict(_PREFILL_LANGUAGES)
_SUPPORTED_PREFILL_LANGUAGE_CODES = {code for code, _label in _PREFILL_LANGUAGES}


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

        category_prompt, allowed_category_ids = await self._build_category_prompt()
        language_prompt = self._build_language_prompt()
        response_data = await self._call_llm(
            normalized_term,
            normalized_language,
            category_prompt,
            language_prompt,
        )
        return self._validate_response(response_data, allowed_category_ids)

    async def generate_draft_for_extracted_entity(
        self,
        entity: ExtractedEntity,
        user_language: str,
    ) -> EntityPrefillDraft:
        """Build a create-entity draft for an LLM-extracted candidate.

        This intentionally reuses the same prompt and validation path as the
        create-entity form so extraction-created entities get the same
        canonicalization, category, display-name, and alias handling.
        """
        term = entity.text_span.strip() or entity.slug.replace("-", " ")
        return await self.generate_draft(term, user_language)

    async def _build_category_prompt(self) -> tuple[str, set[UUID]]:
        result = await self.db.execute(select(UiCategory).order_by(UiCategory.order, UiCategory.id))
        categories = result.scalars().all()
        if not categories:
            return "No UI categories are available. Return null for ui_category_id.", set()

        lines = []
        allowed_category_ids: set[UUID] = set()
        for category in categories:
            allowed_category_ids.add(category.id)
            lines.append(f"- id: {category.id}; label: {json.dumps(category.labels, ensure_ascii=False)}")
        return "Allowed UI categories:\n" + "\n".join(lines), allowed_category_ids

    def _build_language_prompt(self) -> str:
        lines = [f"- {code}: {label}" for code, label in _PREFILL_LANGUAGES]
        return "Available form languages:\n" + "\n".join(lines)

    def _language_label(self, language: str) -> str:
        return _PREFILL_LANGUAGE_LABELS.get(language, language)

    async def _call_llm(
        self,
        term: str,
        user_language: str,
        category_prompt: str,
        language_prompt: str,
    ) -> dict[str, object]:
        system_prompt = (
            "You draft editable metadata for a knowledge-graph entity creation form. "
            "The draft is not authoritative. Do not invent factual claims. "
            "Summaries must be neutral, short descriptions of the entity itself, not evidence claims. "
            "Return only JSON matching the requested shape."
        )
        user_language_label = self._language_label(user_language)
        prompt = f"""
Draft values for a new entity from this user term: {term}
User interface language: {user_language} ({user_language_label})

{category_prompt}

{language_prompt}

Return a JSON object with exactly these fields:
- slug: lowercase URL slug, 3-100 chars, matching ^[a-z][a-z0-9-]*$, based on the canonical English or internationally used entity name
- display_names: object mapping every available form language code to the preferred display name in that language
- summary: object mapping every available form language code to short neutral summary text in that language
- aliases: array of objects with term, language, and term_kind; language may be null for international/no language; term_kind is alias, abbreviation, or brand
- ui_category_id: one allowed category id string or null

Rules:
- Include all available form language codes in display_names.
- Include all available form language codes in summary when a neutral description can be stated.
- Canonicalize slug to the internationally recognized or English entity name, not the user's input language; for example, use fibromyalgia for French Fibromyalgie.
- For medicines, prefer the generic or international nonproprietary name for slug and display_names; do not use a brand name as slug or display name when a generic name is known.
- If the user term is a medicine brand, use the generic or international nonproprietary name in display_names and return the brand only in aliases with term_kind "brand".
- Use the user term as the display name for languages where it is already the standard term.
- Include common alternative names, aliases, synonyms, acronyms, spelling variants, and well-known translated names in aliases.
- Include common longer name variants that add a clinically meaningful qualifier, such as syndrome, disease, condition, salt, formulation, or class wording.
- Set alias language to the matching language code when an alias is language-specific; use null only for language-independent names or symbols.
- For biomedical acronyms and abbreviations commonly used from English terms, set alias language to "en" instead of null.
- Return brand or trade names with term_kind "brand".
- Brand names are proper trade names, not language translations; set brand alias language to null unless the brand name itself is localized.
- For medicines, include a small set of well-known regional brand names for the user interface language market and the available form languages or markets when they are common and useful.
- When the user interface language is not English, also include well-known medicine brand names from that language's primary markets when they are common and useful.
- Return abbreviations and acronyms with term_kind "abbreviation"; use term_kind "alias" for ordinary aliases.
- Include acronyms shorter than 3 characters only when they are useful in this project context, and always mark them as term_kind "abbreviation".
- Do not create abbreviations by taking initials from longer alias variants; include an abbreviation only if it is independently common for the entity itself.
- Do not include dosage- or strength-specific brand variants when the base brand name is already included.
- Do not duplicate any display_names value in aliases, even under another language.
- Do not include speculative aliases, obscure brand names, or relation-like claims.
- Do not include relation claims, treatment claims, efficacy claims, or confidence language.
"""
        try:
            return await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0,
                max_tokens=2400,
            )
        except LLMError as exc:
            raise AppException(
                status_code=502,
                error_code=ErrorCode.LLM_API_ERROR,
                message="AI draft generation failed",
                details="The LLM provider failed while generating entity draft values.",
            ) from exc

    def _validate_response(
        self,
        response_data: dict[str, object],
        allowed_category_ids: set[UUID],
    ) -> EntityPrefillDraft:
        if "ui_category_id" in response_data and response_data["ui_category_id"]:
            try:
                UUID(str(response_data["ui_category_id"]))
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

        display_names = self._clean_language_map(draft.display_names)
        brand_terms = {alias.term.strip().casefold() for alias in draft.aliases if alias.term_kind == "brand"}
        display_names = self._replace_brand_display_names(display_names, brand_terms, draft.slug)
        return EntityPrefillDraft(
            slug=draft.slug,
            display_names=display_names,
            summary=self._clean_language_map(draft.summary, allow_international=False),
            aliases=self._clean_aliases(draft.aliases, display_names),
            ui_category_id=draft.ui_category_id if draft.ui_category_id in allowed_category_ids else None,
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
            if normalized_language and normalized_language not in _SUPPORTED_PREFILL_LANGUAGE_CODES:
                continue
            if normalized_language == "" and not allow_international:
                continue
            normalized_value = value.strip()
            if normalized_value:
                cleaned[normalized_language] = normalized_value
        return cleaned

    def _clean_aliases(
        self,
        aliases: list[EntityPrefillAlias],
        display_names: dict[str, str],
    ) -> list[EntityPrefillAlias]:
        cleaned: list[EntityPrefillAlias] = []
        seen: set[tuple[str, str | None]] = set()
        display_name_terms = {value.strip().casefold() for value in display_names.values() if value.strip()}
        brand_terms: set[str] = set()
        for alias in aliases:
            term = alias.term.strip()
            if not term:
                continue
            if alias.language and alias.language.strip().lower() not in _SUPPORTED_PREFILL_LANGUAGE_CODES:
                continue
            if term.casefold() in display_name_terms:
                continue
            term_kind = self._normalize_alias_kind(alias.term_kind, term)
            language = self._normalize_alias_language(alias.language, term, term_kind)
            if term_kind == "brand" and self._is_dosage_brand_variant(term, brand_terms):
                continue
            key = (term.casefold(), language)
            if key in seen:
                continue
            cleaned.append(EntityPrefillAlias(term=term, language=language, term_kind=term_kind))
            seen.add(key)
            if term_kind == "brand":
                brand_terms.add(term.casefold())
        return cleaned

    def _normalize_alias_kind(self, term_kind: str, term: str) -> str:
        if term_kind == "brand":
            return "brand"
        if term_kind == "abbreviation" or _ACRONYM_PATTERN.fullmatch(term):
            return "abbreviation"
        return "alias"

    def _is_dosage_brand_variant(self, term: str, existing_brand_terms: set[str]) -> bool:
        if not _DOSAGE_OR_STRENGTH_PATTERN.search(term):
            return False
        normalized_term = term.casefold()
        return any(
            normalized_term.startswith(f"{brand} ") or normalized_term.startswith(f"{brand}-")
            for brand in existing_brand_terms
        )

    def _normalize_alias_language(self, language: str | None, term: str, term_kind: str) -> str | None:
        if term_kind == "brand":
            return None
        if language:
            normalized_language = language.strip().lower()
            if (
                _LANGUAGE_PATTERN.fullmatch(normalized_language)
                and normalized_language in _SUPPORTED_PREFILL_LANGUAGE_CODES
            ):
                return normalized_language
        if _ACRONYM_PATTERN.fullmatch(term):
            return "en"
        if _ENGLISH_ALIAS_QUALIFIER_PATTERN.search(term):
            return "en"
        return None

    def _replace_brand_display_names(
        self,
        display_names: dict[str, str],
        brand_terms: set[str],
        slug: str,
    ) -> dict[str, str]:
        if not brand_terms:
            return display_names
        canonical_name = self._display_name_from_slug(slug)
        return {
            language: canonical_name if value.strip().casefold() in brand_terms else value
            for language, value in display_names.items()
        }

    def _display_name_from_slug(self, slug: str) -> str:
        return " ".join(part.capitalize() for part in slug.split("-") if part)

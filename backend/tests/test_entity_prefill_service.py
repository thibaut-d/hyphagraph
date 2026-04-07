from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.llm.base import LLMError
from app.services.entity_prefill_service import EntityPrefillService
from app.utils.errors import AppException


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _ExecuteResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _ScalarResult(self._values)


@pytest.mark.asyncio
async def test_entity_prefill_service_returns_valid_cleaned_draft() -> None:
    category_id = uuid4()
    db = AsyncMock()
    db.execute.return_value = _ExecuteResult([
        SimpleNamespace(id=category_id, labels={"en": "Drug"}, order=1),
    ])
    llm_provider = AsyncMock()
    llm_provider.generate_json.return_value = {
        "slug": "paracetamol",
        "display_names": {
            "international": "Paracetamol",
            "en": "Acetaminophen",
            "fr": "Doliprane",
            "LA": "Paracetamolum",
            "xx": "Invalid language",
        },
        "summary": {"en": "Analgesic and antipyretic drug.", "": "Skipped"},
        "aliases": [
            {"term": "Doliprane", "language": "fr", "term_kind": "brand"},
            {"term": "Doliprane", "language": "fr", "term_kind": "brand"},
            {"term": "Doliprane 500mg", "language": "fr", "term_kind": "brand"},
            {"term": "Panadol", "language": "en", "term_kind": "brand"},
            {"term": "Tylenol", "language": "en", "term_kind": "brand"},
            {"term": "Paracetamol", "language": "fr"},
            {"term": "Acetaminophen", "language": "fr"},
            {"term": "Acetaminophen tablets", "language": "en"},
            {"term": "Acetaminophen syndrome", "language": None},
            {"term": "N-acetyl-para-aminophenol", "language": "international"},
            {"term": "Paracetamolum", "language": "LA"},
            {"term": "Bad code", "language": "xx"},
            {"term": "FM", "language": None},
            {"term": "NSAID", "language": "en"},
        ],
        "ui_category_id": str(category_id),
    }

    draft = await EntityPrefillService(db=db, llm_provider=llm_provider).generate_draft(
        "Paracetamol",
        "en",
    )

    assert draft.slug == "paracetamol"
    assert draft.display_names == {
        "": "Paracetamol",
        "en": "Acetaminophen",
        "fr": "Paracetamol",
        "la": "Paracetamolum",
    }
    assert draft.summary == {"en": "Analgesic and antipyretic drug."}
    assert draft.aliases[0].term == "Doliprane"
    assert draft.aliases[0].language is None
    assert draft.aliases[0].term_kind == "brand"
    assert draft.aliases[1].term == "Panadol"
    assert draft.aliases[1].language is None
    assert draft.aliases[1].term_kind == "brand"
    assert draft.aliases[2].term == "Tylenol"
    assert draft.aliases[2].language is None
    assert draft.aliases[2].term_kind == "brand"
    assert draft.aliases[3].term == "Acetaminophen tablets"
    assert draft.aliases[3].language == "en"
    assert draft.aliases[4].term == "Acetaminophen syndrome"
    assert draft.aliases[4].language == "en"
    assert draft.aliases[5].term == "N-acetyl-para-aminophenol"
    assert draft.aliases[5].language is None
    assert draft.aliases[6].term == "FM"
    assert draft.aliases[6].language == "en"
    assert draft.aliases[6].term_kind == "abbreviation"
    assert draft.aliases[7].term == "NSAID"
    assert draft.aliases[7].language == "en"
    assert draft.aliases[7].term_kind == "abbreviation"
    assert len(draft.aliases) == 8
    assert all(alias.term != "Bad code" for alias in draft.aliases)
    assert all(alias.term != "Paracetamolum" for alias in draft.aliases)
    assert all(alias.term != "Paracetamol" for alias in draft.aliases)
    assert all(alias.term != "Acetaminophen" for alias in draft.aliases)
    assert all(alias.term != "Doliprane 500mg" for alias in draft.aliases)
    assert draft.ui_category_id == category_id
    llm_provider.generate_json.assert_awaited_once()
    prompt = llm_provider.generate_json.await_args.kwargs["prompt"]
    assert "User interface language: en (English)" in prompt
    assert "Available form languages:" in prompt
    assert "- en: English" in prompt
    assert "- fr: French" in prompt
    assert "- ja: Japanese" in prompt
    assert "- la: Latin" in prompt
    assert "based on the canonical English or internationally used entity name" in prompt
    assert "use fibromyalgia for French Fibromyalgie" in prompt
    assert "generic or international nonproprietary name for slug" in prompt
    assert "do not use a brand name as slug or display name" in prompt
    assert "return the brand only in aliases with term_kind \"brand\"" in prompt
    assert "Include all available form language codes in display_names." in prompt
    assert "Include common alternative names, aliases, synonyms" in prompt
    assert "Include common longer name variants that add a clinically meaningful qualifier" in prompt
    assert "Set alias language to the matching language code" in prompt
    assert "For biomedical acronyms and abbreviations commonly used from English terms" in prompt
    assert "Return brand or trade names with term_kind \"brand\"" in prompt
    assert "Brand names are proper trade names, not language translations" in prompt
    assert "well-known regional brand names for the user interface language market" in prompt
    assert "also include well-known medicine brand names from that language's primary markets" in prompt
    assert "Return abbreviations and acronyms with term_kind \"abbreviation\"" in prompt
    assert "Include acronyms shorter than 3 characters only when they are useful" in prompt
    assert "Do not create abbreviations by taking initials from longer alias variants" in prompt
    assert "Do not include dosage- or strength-specific brand variants" in prompt
    assert "Do not include speculative aliases, obscure brand names" in prompt
    assert "Do not duplicate any display_names value in aliases" in prompt
    assert llm_provider.generate_json.await_args.kwargs["max_tokens"] == 2400


@pytest.mark.asyncio
async def test_entity_prefill_service_rejects_llm_api_error() -> None:
    db = AsyncMock()
    db.execute.return_value = _ExecuteResult([])
    llm_provider = AsyncMock()
    llm_provider.generate_json.side_effect = LLMError("provider failed")

    with pytest.raises(AppException) as exc_info:
        await EntityPrefillService(db=db, llm_provider=llm_provider).generate_draft(
            "Paracetamol",
            "en",
        )

    assert exc_info.value.status_code == 502

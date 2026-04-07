from unittest.mock import patch

import pytest

from app.services.pubmed_fetcher import PubMedArticle, PubMedFetcher


class FakeResponse:
    text = "<PubmedArticleSet />"

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, url):
        return FakeResponse()


class EmptyTextPMCFetcher:
    async def fetch_by_pmid(self, pmid):
        return type(
            "PMCArticle",
            (),
            {
                "full_text": "   ",
                "char_count": 0,
                "sections": {},
            },
        )()


@pytest.mark.asyncio
async def test_pubmed_fetch_keeps_abstract_when_pmc_enrichment_is_empty():
    original_article = PubMedArticle(
        pmid="41003152",
        title="Management of Juvenile Fibromyalgia",
        abstract="Juvenile fibromyalgia treatment evidence.",
        authors=[],
        journal="Medical Sciences",
        year=2025,
        doi="10.3390/medsci13030203",
        url="https://pubmed.ncbi.nlm.nih.gov/41003152/",
        full_text="Management of Juvenile Fibromyalgia\n\nJuvenile fibromyalgia treatment evidence.",
    )
    fetcher = PubMedFetcher()

    with patch("app.services.pubmed_fetcher.httpx.AsyncClient", FakeAsyncClient), patch.object(
        fetcher,
        "_parse_pubmed_xml",
        return_value=original_article,
    ), patch("app.services.pubmed_fetcher._load_pmc_fetcher", return_value=EmptyTextPMCFetcher):
        article = await fetcher.fetch_by_pmid("41003152")

    assert article.full_text == original_article.full_text

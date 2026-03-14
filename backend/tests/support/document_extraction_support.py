from app.api.document_extraction_schemas import PubMedBulkSearchRequest, PubMedSearchResult
from app.services.pubmed_fetcher import PubMedArticle
from app.utils.errors import ValidationException


def build_test_pubmed_articles(query: str, max_results: int) -> list[PubMedArticle]:
    normalized_query = query.strip() or "test query"
    slug = normalized_query.lower().replace(" ", "-")
    templates = [
        ("90000001", f"{normalized_query.title()} study overview", "Journal of Test Medicine", 2024),
        ("90000002", f"{normalized_query.title()} evidence update", "Clinical Evidence Review", 2023),
        ("90000003", f"{normalized_query.title()} outcomes analysis", "International Test Reports", 2022),
    ]
    articles: list[PubMedArticle] = []
    for pmid, title, journal, year in templates[:max_results]:
        articles.append(
            PubMedArticle(
                pmid=pmid,
                title=title,
                abstract=f"Deterministic testing abstract for {normalized_query}.",
                authors=["Test Author", "Co Author"],
                journal=journal,
                year=year,
                doi=f"10.1000/{slug}-{pmid}",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                full_text=f"{title}\n\nDeterministic testing abstract for {normalized_query}.",
            )
        )
    return articles


def get_test_pubmed_articles_for_pmids(pmids: list[str]) -> list[PubMedArticle]:
    articles = build_test_pubmed_articles("test import", max(len(pmids), 1))
    by_pmid = {article.pmid: article for article in articles}
    return [by_pmid[pmid] for pmid in pmids if pmid in by_pmid]


def build_pubmed_search_results(articles: list[PubMedArticle]) -> list[PubMedSearchResult]:
    return [
        PubMedSearchResult(
            pmid=article.pmid,
            title=article.title,
            authors=article.authors,
            journal=article.journal,
            year=article.year,
            doi=article.doi,
            url=article.url,
        )
        for article in articles
    ]


def resolve_pubmed_bulk_query(
    request: PubMedBulkSearchRequest,
    *,
    query_from_url: str | None,
) -> str:
    if request.query:
        return request.query

    if request.search_url:
        if query_from_url:
            return query_from_url
        raise ValidationException(
            message="Could not extract search query from URL",
            field="search_url",
            details=f"Failed to parse query from URL: {request.search_url}",
            context={"search_url": request.search_url},
        )

    raise ValidationException(
        message="Either 'query' or 'search_url' must be provided",
        details="Provide either a direct search query or a PubMed search URL",
    )

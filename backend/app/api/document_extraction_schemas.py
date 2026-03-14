from uuid import UUID

from pydantic import BaseModel


class UrlExtractionRequest(BaseModel):
    url: str


class PubMedBulkSearchRequest(BaseModel):
    query: str | None = None
    search_url: str | None = None
    max_results: int = 10


class PubMedSearchResult(BaseModel):
    pmid: str
    title: str
    authors: list[str]
    journal: str | None
    year: int | None
    doi: str | None
    url: str


class PubMedBulkSearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[PubMedSearchResult]
    retrieved_count: int


class PubMedBulkImportRequest(BaseModel):
    pmids: list[str]


class PubMedBulkImportResponse(BaseModel):
    total_requested: int
    sources_created: int
    failed_pmids: list[str]
    source_ids: list[UUID]


class SmartDiscoveryRequest(BaseModel):
    entity_slugs: list[str]
    max_results: int = 20
    min_quality: float = 0.5
    databases: list[str] = ["pubmed"]


class SmartDiscoveryResult(BaseModel):
    pmid: str | None = None
    title: str
    authors: list[str]
    journal: str | None
    year: int | None
    doi: str | None
    url: str
    trust_level: float
    relevance_score: float
    database: str
    already_imported: bool = False


class SmartDiscoveryResponse(BaseModel):
    entity_slugs: list[str]
    query_used: str
    total_found: int
    results: list[SmartDiscoveryResult]
    databases_searched: list[str]

from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


SUPPORTED_DISCOVERY_DATABASES = ("pubmed",)


class DiscoveryResponseModel(BaseModel):
    @classmethod
    def from_summary(cls, summary):
        return cls.model_validate(summary)


class UrlExtractionRequest(BaseModel):
    url: str


class PubMedBulkSearchRequest(BaseModel):
    query: str | None = None
    search_url: str | None = None
    max_results: int = Field(default=10, ge=1, le=100)


class PubMedSearchResult(BaseModel):
    pmid: str
    title: str
    authors: list[str]
    journal: str | None
    year: int | None
    doi: str | None
    url: str


class PubMedBulkSearchResponse(DiscoveryResponseModel):
    query: str
    total_results: int
    results: list[PubMedSearchResult]
    retrieved_count: int

    @model_validator(mode="before")
    @classmethod
    def build_results_from_summary(cls, value):
        if isinstance(value, dict):
            return value

        return {
            "query": value.query,
            "total_results": value.total_results,
            "results": [
                {
                    "pmid": article.pmid,
                    "title": article.title,
                    "authors": article.authors,
                    "journal": article.journal,
                    "year": article.year,
                    "doi": article.doi,
                    "url": article.url,
                }
                for article in value.results
            ],
            "retrieved_count": value.retrieved_count,
        }


class PubMedBulkImportRequest(BaseModel):
    pmids: list[str]
    discovery_query: str | None = None

    @field_validator("pmids")
    @classmethod
    def validate_pmids(cls, value: list[str]) -> list[str]:
        cleaned = []
        for pmid in value:
            normalized = pmid.strip()
            if not normalized:
                raise ValueError("PMIDs must be non-empty strings")
            cleaned.append(normalized)
        return cleaned


class PubMedBulkImportResponse(DiscoveryResponseModel):
    total_requested: int
    sources_created: int
    failed_pmids: list[str]
    skipped_pmids: list[str] = []
    source_ids: list[UUID]

    @model_validator(mode="before")
    @classmethod
    def build_from_summary(cls, value):
        if isinstance(value, dict):
            return value

        return {
            "total_requested": value.total_requested,
            "sources_created": value.sources_created,
            "failed_pmids": value.failed_pmids,
            "skipped_pmids": value.skipped_pmids,
            "source_ids": value.source_ids,
        }


class SmartDiscoveryRequest(BaseModel):
    entity_slugs: list[str]
    max_results: int = Field(default=20, ge=1, le=100)
    min_quality: float = Field(default=0.5, ge=0.0, le=1.0)
    databases: list[str] = Field(default_factory=lambda: ["pubmed"])

    @field_validator("entity_slugs")
    @classmethod
    def validate_entity_slugs(cls, value: list[str]) -> list[str]:
        cleaned = []
        for slug in value:
            normalized = slug.strip()
            if not normalized:
                raise ValueError("Entity slugs must be non-empty strings")
            cleaned.append(normalized)
        return cleaned

    @field_validator("databases")
    @classmethod
    def validate_databases(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one database must be selected")

        invalid = [database for database in value if database not in SUPPORTED_DISCOVERY_DATABASES]
        if invalid:
            supported = ", ".join(SUPPORTED_DISCOVERY_DATABASES)
            invalid_joined = ", ".join(invalid)
            raise ValueError(
                f"Unsupported database(s): {invalid_joined}. Supported databases: {supported}"
            )
        return value


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


class SmartDiscoveryResponse(DiscoveryResponseModel):
    entity_slugs: list[str]
    query_used: str
    total_found: int
    results: list[SmartDiscoveryResult]
    databases_searched: list[str]

    @model_validator(mode="before")
    @classmethod
    def build_results_from_summary(cls, value):
        if isinstance(value, dict):
            return value

        return {
            "entity_slugs": value.entity_slugs,
            "query_used": value.query_used,
            "total_found": value.total_found,
            "results": [
                {
                    "pmid": item.pmid,
                    "title": item.title,
                    "authors": item.authors,
                    "journal": item.journal,
                    "year": item.year,
                    "doi": item.doi,
                    "url": item.url,
                    "trust_level": item.trust_level,
                    "relevance_score": item.relevance_score,
                    "database": item.database,
                    "already_imported": item.already_imported,
                }
                for item in value.results
            ],
            "databases_searched": value.databases_searched,
        }

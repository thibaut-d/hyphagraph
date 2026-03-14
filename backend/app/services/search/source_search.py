from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.schemas.search import SearchFilters, SourceSearchResult

from .common import build_snippet, execute_ranked_query, json_text_contains, text_contains


async def search_sources(
    db: AsyncSession, filters: SearchFilters
) -> tuple[list[SourceSearchResult], int]:
    query_lower = filters.query.lower()

    base_query = (
        select(Source, SourceRevision)
        .join(SourceRevision, Source.id == SourceRevision.source_id)
        .where(SourceRevision.is_current == True)
    )

    if filters.source_kind:
        base_query = base_query.where(SourceRevision.kind.in_(filters.source_kind))

    base_query = base_query.where(
        or_(
            text_contains(SourceRevision.title, query_lower),
            text_contains(SourceRevision.origin, query_lower),
            json_text_contains(SourceRevision.authors, query_lower),
        )
    )

    relevance_score = case(
        (func.lower(SourceRevision.title) == query_lower, 1.0),
        (text_contains(SourceRevision.title, query_lower), 0.9),
        (json_text_contains(SourceRevision.authors, query_lower), 0.7),
        else_=0.5,
    ).label("relevance")

    def map_row(row: tuple[Source, SourceRevision, float | None]) -> SourceSearchResult:
        source, revision, score = row
        return SourceSearchResult(
            id=source.id,
            type="source",
            title=revision.title,
            snippet=build_snippet(revision.summary),
            relevance_score=float(score) if score else 0.5,
            kind=revision.kind,
            year=revision.year,
            authors=revision.authors,
            trust_level=revision.trust_level,
        )

    return await execute_ranked_query(
        db,
        base_query=base_query,
        relevance_score=relevance_score,
        order_by=(
            relevance_score.desc(),
            SourceRevision.year.desc().nullslast(),
            Source.created_at.desc(),
        ),
        limit=filters.limit,
        offset=filters.offset,
        map_row=map_row,
    )

from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.schemas.search import EntitySearchResult, SearchFilters

from .common import build_snippet, execute_ranked_query, json_text_contains, text_contains


async def search_entities(
    db: AsyncSession, filters: SearchFilters
) -> tuple[list[EntitySearchResult], int]:
    query_lower = filters.query.lower()

    base_query = (
        select(Entity, EntityRevision)
        .join(EntityRevision, Entity.id == EntityRevision.entity_id)
        .outerjoin(EntityTerm, Entity.id == EntityTerm.entity_id)
        .where(EntityRevision.is_current == True)
    )

    if filters.ui_category_id:
        base_query = base_query.where(
            EntityRevision.ui_category_id.in_([UUID(category_id) for category_id in filters.ui_category_id])
        )

    base_query = base_query.where(
        or_(
            text_contains(EntityRevision.slug, query_lower),
            json_text_contains(EntityRevision.summary, query_lower),
            text_contains(EntityTerm.term, query_lower),
        )
    ).distinct()

    relevance_score = case(
        (func.lower(EntityRevision.slug) == query_lower, 1.0),
        (func.lower(EntityTerm.term) == query_lower, 0.95),
        (text_contains(EntityRevision.slug, query_lower), 0.8),
        (text_contains(EntityTerm.term, query_lower), 0.7),
        else_=0.5,
    ).label("relevance")

    def map_row(row: tuple[Entity, EntityRevision, float | None]) -> EntitySearchResult:
        entity, revision, score = row
        return EntitySearchResult(
            id=entity.id,
            type="entity",
            title=revision.slug,
            slug=revision.slug,
            snippet=build_snippet(revision.summary),
            relevance_score=float(score) if score else 0.5,
            ui_category_id=revision.ui_category_id,
            summary=revision.summary,
        )

    return await execute_ranked_query(
        db,
        base_query=base_query,
        relevance_score=relevance_score,
        order_by=(relevance_score.desc(), Entity.created_at.desc()),
        limit=filters.limit,
        offset=filters.offset,
        map_row=map_row,
    )

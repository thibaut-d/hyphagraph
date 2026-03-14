from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.schemas.search import RelationSearchResult, SearchFilters

from .common import build_snippet, execute_ranked_query, json_text_contains, text_contains


async def search_relations(
    db: AsyncSession, filters: SearchFilters
) -> tuple[list[RelationSearchResult], int]:
    query_lower = filters.query.lower()

    base_query = (
        select(Relation, RelationRevision)
        .join(RelationRevision, Relation.id == RelationRevision.relation_id)
        .where(RelationRevision.is_current == True)
        .where(
            or_(
                text_contains(RelationRevision.kind, query_lower),
                json_text_contains(RelationRevision.notes, query_lower),
            )
        )
    )

    relevance_score = case(
        (func.lower(RelationRevision.kind) == query_lower, 1.0),
        (text_contains(RelationRevision.kind, query_lower), 0.8),
        else_=0.5,
    ).label("relevance")

    async def map_row(
        row: tuple[Relation, RelationRevision, float | None]
    ) -> RelationSearchResult:
        relation, revision, score = row
        role_rows = await db.execute(
            select(RelationRoleRevision.entity_id).where(
                RelationRoleRevision.relation_revision_id == revision.id
            )
        )
        entity_ids = [entity_id for (entity_id,) in role_rows.all()]

        return RelationSearchResult(
            id=relation.id,
            type="relation",
            title=revision.kind or "Relation",
            snippet=build_snippet(revision.notes),
            relevance_score=float(score) if score else 0.5,
            kind=revision.kind,
            source_id=relation.source_id,
            entity_ids=entity_ids,
            direction=revision.direction,
        )

    return await execute_ranked_query(
        db,
        base_query=base_query,
        relevance_score=relevance_score,
        order_by=(relevance_score.desc(), Relation.created_at.desc()),
        limit=filters.limit,
        offset=filters.offset,
        map_row=map_row,
    )

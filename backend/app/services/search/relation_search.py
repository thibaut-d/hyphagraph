from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.schemas.search import RelationSearchResult, SearchFilters

from .common import build_snippet, json_text_contains, text_contains


async def search_relations(
    db: AsyncSession, filters: SearchFilters
) -> tuple[list[RelationSearchResult], int]:
    query_lower = filters.query.lower()

    base_query = (
        select(Relation, RelationRevision)
        .join(RelationRevision, Relation.id == RelationRevision.relation_id)
        .where(RelationRevision.is_current == True)
        .where(RelationRevision.status == "confirmed")
        .where(Relation.is_rejected == False)
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

    # Count total
    count_stmt = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Paginated rows
    query_with_score = (
        base_query.add_columns(relevance_score)
        .order_by(relevance_score.desc(), Relation.created_at.desc())
        .limit(filters.limit)
        .offset(filters.offset)
    )
    rows = (await db.execute(query_with_score)).all()

    if not rows:
        return [], total

    # Batch-load roles (DF-SCH-M3: single query instead of N+1)
    revision_ids = [revision.id for (_, revision, _) in rows]
    roles_stmt = select(
        RelationRoleRevision.relation_revision_id,
        RelationRoleRevision.entity_id,
    ).where(RelationRoleRevision.relation_revision_id.in_(revision_ids))
    roles_result = await db.execute(roles_stmt)
    roles_by_revision: dict = {}
    for revision_id, entity_id in roles_result.all():
        roles_by_revision.setdefault(revision_id, []).append(entity_id)

    results = [
        RelationSearchResult(
            id=relation.id,
            type="relation",
            title=revision.kind or "Relation",
            snippet=build_snippet(revision.notes),
            relevance_score=float(score) if score else 0.5,
            kind=revision.kind,
            source_id=relation.source_id,
            entity_ids=roles_by_revision.get(revision.id, []),
            direction=revision.direction,
        )
        for relation, revision, score in rows
    ]

    return results, total

from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol, TypeVar

from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement, Select

ResultT = TypeVar("ResultT")
RowT = TypeVar("RowT")


class SupportsStringValues(Protocol):
    def values(self) -> object: ...


def json_text_contains(column: object, query_lower: str) -> ColumnElement[bool]:
    return func.lower(func.cast(column, String)).contains(query_lower)


def text_contains(column: object, query_lower: str) -> ColumnElement[bool]:
    return func.lower(column).contains(query_lower)


def build_snippet(
    value: SupportsStringValues | str | None,
    max_length: int = 150,
) -> str | None:
    text: str | None = None

    if value is not None and hasattr(value, "values"):
        text = next((item for item in value.values() if isinstance(item, str)), None)
    elif isinstance(value, str):
        text = value

    if not text:
      return None

    return f"{text[:max_length]}..." if len(text) > max_length else text


async def execute_ranked_query(
    db: AsyncSession,
    *,
    base_query: Select[tuple[RowT]],
    relevance_score: ColumnElement[float],
    order_by: Sequence[ColumnElement[object]],
    limit: int,
    offset: int,
    map_row: Callable[[RowT], Awaitable[ResultT] | ResultT],
) -> tuple[list[ResultT], int]:
    count_stmt = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    query_with_score = base_query.add_columns(relevance_score).order_by(*order_by)
    query_with_score = query_with_score.limit(limit).offset(offset)

    rows = (await db.execute(query_with_score)).all()

    results: list[ResultT] = []
    for row in rows:
        mapped = map_row(row)
        if isinstance(mapped, Awaitable):
            results.append(await mapped)
        else:
            results.append(mapped)

    return results, total

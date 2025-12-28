from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, cast, String, func
from fastapi import HTTPException, status
from typing import Optional, Tuple

from app.schemas.source import SourceWrite, SourceRead
from app.schemas.filters import SourceFilters, SourceFilterOptions
from app.repositories.source_repo import SourceRepository
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.mappers.source_mapper import (
    source_revision_from_write,
    source_to_read,
)
from app.utils.revision_helpers import get_current_revision, create_new_revision


class SourceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SourceRepository(db)

    async def create(self, payload: SourceWrite, user_id=None) -> SourceRead:
        """
        Create a new source with its first revision.

        Creates both:
        1. Base Source (immutable, just id + created_at)
        2. SourceRevision (all the data)
        """
        try:
            # Create base source
            source = Source()
            self.db.add(source)
            await self.db.flush()  # Get the source.id

            # Create first revision
            revision_data = source_revision_from_write(payload)
            if user_id:
                revision_data['created_by_user_id'] = user_id

            revision = await create_new_revision(
                db=self.db,
                revision_class=SourceRevision,
                parent_id_field='source_id',
                parent_id=source.id,
                revision_data=revision_data,
                set_as_current=True,
            )

            await self.db.commit()
            return source_to_read(source, revision)

        except Exception:
            await self.db.rollback()
            raise

    async def get(self, source_id) -> SourceRead:
        """Get source with its current revision."""
        source = await self.repo.get_by_id(source_id)
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found",
            )

        # Get current revision
        current_revision = await get_current_revision(
            db=self.db,
            revision_class=SourceRevision,
            parent_id_field='source_id',
            parent_id=source.id,
        )

        return source_to_read(source, current_revision)

    async def list_all(self, filters: Optional[SourceFilters] = None) -> Tuple[list[SourceRead], int]:
        """
        List all sources with their current revisions, optionally filtered and paginated.

        Filters are applied to the current revision data:
        - kind: Filter by kind field (OR logic for multiple values)
        - year_min/year_max: Filter by publication year range
        - trust_level_min/trust_level_max: Filter by trust level range
        - search: Case-insensitive search in title, authors, or origin
        - limit: Maximum number of results to return
        - offset: Number of results to skip

        Returns:
            Tuple of (items, total_count)
        """
        # Build base query for sources with their current revisions
        base_query = (
            select(Source, SourceRevision)
            .join(SourceRevision, Source.id == SourceRevision.source_id)
            .where(SourceRevision.is_current == True)
        )

        # Apply filters if provided
        if filters:
            # Filter by kind (OR logic)
            if filters.kind:
                base_query = base_query.where(SourceRevision.kind.in_(filters.kind))

            # Filter by year range
            if filters.year_min is not None:
                base_query = base_query.where(SourceRevision.year >= filters.year_min)
            if filters.year_max is not None:
                base_query = base_query.where(SourceRevision.year <= filters.year_max)

            # Filter by trust level range
            if filters.trust_level_min is not None:
                base_query = base_query.where(SourceRevision.trust_level >= filters.trust_level_min)
            if filters.trust_level_max is not None:
                base_query = base_query.where(SourceRevision.trust_level <= filters.trust_level_max)

            # Search in title, authors, or origin (case-insensitive)
            if filters.search:
                search_term = f"%{filters.search.lower()}%"
                # Convert authors array to string for searching
                base_query = base_query.where(
                    or_(
                        SourceRevision.title.ilike(search_term),
                        SourceRevision.origin.ilike(search_term),
                        cast(SourceRevision.authors, String).ilike(search_term),
                    )
                )

        # Count total results before pagination
        count_query = select(func.count()).select_from(
            base_query.subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination to items query
        limit = filters.limit if filters else 50
        offset = filters.offset if filters else 0
        items_query = base_query.limit(limit).offset(offset)

        # Execute items query
        result_rows = await self.db.execute(items_query)
        results = result_rows.all()

        # Convert to SourceRead objects
        items = [source_to_read(source, revision) for source, revision in results]

        return items, total

    async def update(self, source_id: str, payload: SourceWrite, user_id=None) -> SourceRead:
        """
        Update a source by creating a new revision.

        The base Source remains immutable. This creates a new SourceRevision
        with is_current=True and marks the old revision as is_current=False.
        """
        try:
            # Verify source exists
            source = await self.repo.get_by_id(source_id)
            if not source:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Source not found",
                )

            # Create new revision with updated data
            revision_data = source_revision_from_write(payload)
            if user_id:
                revision_data['created_by_user_id'] = user_id

            revision = await create_new_revision(
                db=self.db,
                revision_class=SourceRevision,
                parent_id_field='source_id',
                parent_id=source.id,
                revision_data=revision_data,
                set_as_current=True,
            )

            await self.db.commit()
            return source_to_read(source, revision)

        except HTTPException:
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def delete(self, source_id: str) -> None:
        """
        Delete a source and all its revisions.

        Note: This is a hard delete. Consider implementing soft delete
        by adding a deleted_at field if needed.
        """
        try:
            source = await self.repo.get_by_id(source_id)
            if not source:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Source not found",
                )

            # Delete the source (cascade should handle revisions)
            await self.repo.delete(source)
            await self.db.commit()

        except HTTPException:
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def get_filter_options(self) -> SourceFilterOptions:
        """
        Get available filter options for sources.

        Returns distinct values for filterable fields using efficient database aggregation.
        This avoids fetching all records when populating filter UI controls.

        Returns:
            SourceFilterOptions with available kinds and year range
        """
        # Get distinct kinds (only from current revisions)
        kind_query = select(SourceRevision.kind).distinct().where(
            SourceRevision.is_current == True
        )
        kinds_result = await self.db.execute(kind_query)
        kinds = [k for (k,) in kinds_result.all() if k is not None]

        # Get min/max year using aggregation (only from current revisions)
        year_query = select(
            func.min(SourceRevision.year),
            func.max(SourceRevision.year)
        ).where(SourceRevision.is_current == True)
        year_result = await self.db.execute(year_query)
        min_year, max_year = year_result.one()

        return SourceFilterOptions(
            kinds=sorted(kinds),
            year_range=(min_year, max_year) if min_year and max_year else None,
        )
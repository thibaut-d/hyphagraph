from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.source import SourceWrite, SourceRead
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

    async def list_all(self) -> list[SourceRead]:
        """List all sources with their current revisions."""
        sources = await self.repo.list_all()

        # Get current revisions for all sources
        result = []
        for source in sources:
            current_revision = await get_current_revision(
                db=self.db,
                revision_class=SourceRevision,
                parent_id_field='source_id',
                parent_id=source.id,
            )
            result.append(source_to_read(source, current_revision))

        return result
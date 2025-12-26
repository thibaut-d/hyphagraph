from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.relation import RelationWrite, RelationRead
from app.repositories.relation_repo import RelationRepository
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.mappers.relation_mapper import (
    relation_revision_from_write,
    relation_to_read,
)
from app.services.validation_service import validate_relation
from app.utils.revision_helpers import get_current_revision, create_new_revision


class RelationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RelationRepository(db)

    async def create(self, payload: RelationWrite, user_id=None) -> RelationRead:
        """
        Create a new relation with its first revision.

        Creates:
        1. Base Relation (immutable, just id + created_at + source_id)
        2. RelationRevision (all mutable data)
        3. RelationRoleRevisions (roles tied to this revision)
        """
        # 1. Structural validation
        validate_relation(payload)

        try:
            # 2. Create base relation
            relation = Relation(source_id=payload.source_id)
            self.db.add(relation)
            await self.db.flush()  # Get the relation.id

            # 3. Create first revision
            revision_data = relation_revision_from_write(payload)
            if user_id:
                revision_data['created_by_user_id'] = user_id

            revision = await create_new_revision(
                db=self.db,
                revision_class=RelationRevision,
                parent_id_field='relation_id',
                parent_id=relation.id,
                revision_data=revision_data,
                set_as_current=True,
            )

            # 4. Create role revisions (snapshot of roles for this revision)
            for role_data in payload.roles:
                role_revision = RelationRoleRevision(
                    relation_revision_id=revision.id,
                    entity_id=role_data.entity_id,
                    role_type=role_data.role_type,
                    weight=role_data.weight,
                    coverage=role_data.coverage,
                )
                self.db.add(role_revision)

            await self.db.flush()  # Ensure roles are created

            # 5. Commit transaction
            await self.db.commit()

            # 6. Refresh to get the roles relationship populated
            await self.db.refresh(revision, ['roles'])

            # 7. Return Read
            return relation_to_read(relation, revision)

        except Exception:
            await self.db.rollback()
            raise

    async def get(self, relation_id) -> RelationRead:
        """Get relation with its current revision."""
        relation = await self.repo.get_by_id(relation_id)
        if not relation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relation not found",
            )

        # Get current revision with roles eagerly loaded
        current_revision = await get_current_revision(
            db=self.db,
            revision_class=RelationRevision,
            parent_id_field='relation_id',
            parent_id=relation.id,
            load_relationships=['roles'],
        )

        return relation_to_read(relation, current_revision)

    async def list_by_source(self, source_id) -> list[RelationRead]:
        """List all relations for a source with their current revisions."""
        relations = await self.repo.list_by_source(source_id)

        # Get current revisions for all relations with roles eagerly loaded
        result = []
        for relation in relations:
            current_revision = await get_current_revision(
                db=self.db,
                revision_class=RelationRevision,
                parent_id_field='relation_id',
                parent_id=relation.id,
                load_relationships=['roles'],
            )
            result.append(relation_to_read(relation, current_revision))

        return result
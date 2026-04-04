import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import String, and_, case, cast, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.mappers.source_mapper import source_revision_from_write, source_to_read
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.repositories.source_repo import SourceRepository
from app.schemas.filters import SourceFilterOptions, SourceFilters
from app.schemas.source import SourceWrite, SourceRead
from app.services.derived_properties_service import DerivedPropertiesService
from app.services.query_predicates import canonical_relation_predicate
from app.utils.errors import SourceNotFoundException
from app.utils.revision_helpers import create_new_revision, get_current_revision

logger = logging.getLogger(__name__)

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "cardiology": ["cardio", "heart", "cardiac", "cardiovascular"],
    "neurology": ["neuro", "brain", "neural", "cognitive"],
    "psychiatry": ["psychiatry", "mental", "psychology", "behavioral"],
    "oncology": ["cancer", "oncology", "tumor", "carcinoma"],
    "endocrinology": ["endocrine", "diabetes", "hormone", "metabolic"],
    "immunology": ["immune", "immunology", "antibody", "vaccine"],
    "gastroenterology": ["gastro", "digestive", "intestinal", "gi"],
    "nephrology": ["kidney", "renal", "nephrology"],
    "pulmonology": ["lung", "respiratory", "pulmonary"],
    "rheumatology": ["rheumat", "arthritis", "autoimmune"],
}


class SourceService:
    def __init__(
        self,
        db: AsyncSession,
        derived_properties_service: DerivedPropertiesService | None = None,
    ):
        self.db = db
        self.repo = SourceRepository(db)
        self.derived_properties_service = (
            derived_properties_service or DerivedPropertiesService(db)
        )

    async def create(self, payload: SourceWrite, user_id: UUID | None = None) -> SourceRead:
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
            if not user_id:
                logger.warning("Creating source revision without user attribution (user_id=None) for title=%s", payload.title)
            else:
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

        except Exception as e:
            logger.error("Failed to create source '%s': %s", payload.title, e, exc_info=True)
            await self.db.rollback()
            raise

    async def get(self, source_id) -> SourceRead:
        """Get source with its current revision."""
        source = await self.repo.get_by_id(source_id)
        if not source:
            raise SourceNotFoundException(
                source_id=str(source_id)
            )

        # Get current revision
        current_revision = await get_current_revision(
            db=self.db,
            revision_class=SourceRevision,
            parent_id_field='source_id',
            parent_id=source.id,
        )
        if current_revision is None or current_revision.status != "confirmed":
            raise SourceNotFoundException(source_id=str(source_id))

        return source_to_read(source, current_revision)

    async def list_all(self, filters: Optional[SourceFilters] = None) -> Tuple[list[SourceRead], int]:
        """
        List all sources with their current revisions, optionally filtered and paginated.

        Filters are applied to the current revision data:
        - kind: Filter by kind field (OR logic for multiple values)
        - year_min/year_max: Filter by publication year range
        - trust_level_min/trust_level_max: Filter by trust level range
        - search: Case-insensitive search in title, authors, or origin
        - domain: Filter by medical domain (advanced)
        - role: Filter by role in graph (advanced)
        - limit: Maximum number of results to return
        - offset: Number of results to skip

        Returns:
            Tuple of (items, total_count)
        """
        base_query = self._build_list_query(filters)
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        limit = filters.limit if filters else 50
        offset = filters.offset if filters else 0
        items_query = base_query.limit(limit).offset(offset)
        result_rows = await self.db.execute(items_query)
        items = self._map_list_rows(result_rows.all())
        return items, total

    def _build_list_query(self, filters: Optional[SourceFilters]) -> Select:
        query = (
            select(Source, SourceRevision)
            .join(SourceRevision, Source.id == SourceRevision.source_id)
            .where(SourceRevision.is_current == True)
            .where(SourceRevision.status == "confirmed")
        )

        if not filters:
            return query

        query = self._apply_basic_filters(query, filters)
        query = self._apply_domain_filters(query, filters.domain)
        query = self._apply_role_filters(query, filters.role)
        return query

    def _apply_basic_filters(self, query: Select, filters: SourceFilters) -> Select:
        if filters.kind:
            query = query.where(SourceRevision.kind.in_(filters.kind))

        if filters.year_min is not None:
            query = query.where(SourceRevision.year >= filters.year_min)
        if filters.year_max is not None:
            query = query.where(SourceRevision.year <= filters.year_max)

        if filters.trust_level_min is not None:
            query = query.where(SourceRevision.trust_level >= filters.trust_level_min)
        if filters.trust_level_max is not None:
            query = query.where(SourceRevision.trust_level <= filters.trust_level_max)

        if filters.search:
            search_pattern = f"%{filters.search.lower()}%"
            query = query.where(
                or_(
                    SourceRevision.title.ilike(search_pattern),
                    SourceRevision.origin.ilike(search_pattern),
                    cast(SourceRevision.authors, String).ilike(search_pattern),
                )
            )

        return query

    def _apply_domain_filters(
        self,
        query: Select,
        domains: Optional[list[str]],
    ) -> Select:
        if not domains:
            return query

        domain_conditions = []
        for domain in domains:
            keyword_conditions = self._build_domain_keyword_conditions(domain)
            if keyword_conditions:
                domain_conditions.append(or_(*keyword_conditions))

        if not domain_conditions:
            return query

        return query.where(or_(*domain_conditions))

    def _build_domain_keyword_conditions(self, domain: str) -> list:
        keyword_conditions = []
        for keyword in DOMAIN_KEYWORDS.get(domain, []):
            keyword_pattern = f"%{keyword}%"
            keyword_conditions.append(
                or_(
                    SourceRevision.origin.ilike(keyword_pattern),
                    SourceRevision.title.ilike(keyword_pattern),
                )
            )
        return keyword_conditions

    def _apply_role_filters(
        self,
        query: Select,
        roles: Optional[list[str]],
    ) -> Select:
        if not roles:
            return query

        relation_stats = self._build_relation_stats_subquery()
        query = query.join(
            relation_stats,
            Source.id == relation_stats.c.source_id,
            isouter=True,
        )

        role_conditions = []
        if "pillar" in roles:
            role_conditions.append(relation_stats.c.relation_count > 5)
        if "supporting" in roles:
            role_conditions.append(
                and_(
                    relation_stats.c.relation_count >= 2,
                    relation_stats.c.relation_count <= 5,
                )
            )
        if "contradictory" in roles:
            role_conditions.append(relation_stats.c.contradictory_count > 0)
        if "single" in roles:
            role_conditions.append(relation_stats.c.relation_count == 1)

        if not role_conditions:
            return query

        return query.where(or_(*role_conditions))

    def _build_relation_stats_subquery(self):
        return (
            select(
                Relation.source_id,
                func.count(distinct(Relation.id)).label("relation_count"),
                func.sum(
                    case(
                        (RelationRevision.direction == "contradicts", 1),
                        else_=0,
                    )
                ).label("contradictory_count"),
            )
            .join(RelationRevision, Relation.id == RelationRevision.relation_id)
            .where(canonical_relation_predicate())
            .group_by(Relation.source_id)
            .subquery()
        )

    def _map_list_rows(self, rows) -> list[SourceRead]:
        items: list[SourceRead] = []
        for row in rows:
            source = row[0]
            revision = row[1] if len(row) > 1 else None
            if source and revision:
                items.append(source_to_read(source, revision))
        return items

    async def update(self, source_id: str, payload: SourceWrite, user_id: UUID | None = None) -> SourceRead:
        """
        Update a source by creating a new revision.

        The base Source remains immutable. This creates a new SourceRevision
        with is_current=True and marks the old revision as is_current=False.
        """
        try:
            # Verify source exists
            source = await self.repo.get_by_id(source_id)
            if not source:
                raise SourceNotFoundException(
                    source_id=str(source_id)
                )

            # Create new revision with updated data
            revision_data = source_revision_from_write(payload)
            if not user_id:
                logger.warning("Updating source revision without user attribution (user_id=None) for source_id=%s", source_id)
            else:
                revision_data['created_by_user_id'] = user_id

            revision = await create_new_revision(
                db=self.db,
                revision_class=SourceRevision,
                parent_id_field='source_id',
                parent_id=source.id,
                revision_data=revision_data,
                set_as_current=True,
            )

            # Invalidate inference cache for all entities linked to this source.
            # Source trust_level changes affect evidence quality calculations, so
            # any computed relation that references a relation from this source is stale.
            entity_ids_stmt = (
                select(RelationRoleRevision.entity_id)
                .join(
                    RelationRevision,
                    RelationRoleRevision.relation_revision_id == RelationRevision.id,
                )
                .join(Relation, RelationRevision.relation_id == Relation.id)
                .where(
                    Relation.source_id == source.id,
                    canonical_relation_predicate(),
                )
                .distinct()
            )
            entity_ids_result = await self.db.execute(entity_ids_stmt)
            affected_entity_ids = [row[0] for row in entity_ids_result.all()]
            if affected_entity_ids:
                computed_repo = ComputedRelationRepository(self.db)
                for entity_id in affected_entity_ids:
                    await computed_repo.delete_by_entity_id(entity_id)

            await self.db.commit()
            return source_to_read(source, revision)

        except SourceNotFoundException:
            raise
        except Exception as e:
            logger.error("Failed to update source %s: %s", source_id, e, exc_info=True)
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
                raise SourceNotFoundException(
                    source_id=str(source_id)
                )

            # Delete the source (cascade should handle revisions)
            await self.repo.delete(source)
            await self.db.commit()

        except SourceNotFoundException:
            raise
        except Exception as e:
            logger.error("Failed to delete source %s: %s", source_id, e, exc_info=True)
            await self.db.rollback()
            raise

    async def get_filter_options(self) -> SourceFilterOptions:
        """
        Get available filter options for sources.

        Returns distinct values for filterable fields using efficient database aggregation.
        This avoids fetching all records when populating filter UI controls.

        Returns:
            SourceFilterOptions with available kinds, year range, and advanced options
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

        # Get advanced filter options using derived properties service
        # Get available domains
        domains = await self.derived_properties_service.get_all_domains()

        return SourceFilterOptions(
            kinds=sorted(kinds),
            year_range=(min_year, max_year) if min_year and max_year else None,
            domains=domains,
            roles=["pillar", "supporting", "contradictory", "single"],
        )

    async def add_document_to_source(
        self,
        source_id: UUID,
        document_text: str,
        document_format: str,
        document_file_name: str,
        user_id: UUID | None = None
    ) -> None:
        """
        Add document content to a source by creating a new current revision.

        The previous current revision remains immutable history. The new revision
        copies the existing source metadata and appends the uploaded document data.

        Args:
            source_id: The source to update
            document_text: Extracted text content
            document_format: File format (pdf, txt, etc.)
            document_file_name: Original filename
            user_id: User who uploaded the document

        Raises:
            HTTPException: If source not found
        """
        try:
            # Get the source
            source = await self.repo.get_by_id(source_id)
            if not source:
                raise SourceNotFoundException(
                    source_id=str(source_id)
                )

            current_revision = await get_current_revision(
                db=self.db,
                revision_class=SourceRevision,
                parent_id_field="source_id",
                parent_id=source_id,
            )

            if not current_revision:
                raise SourceNotFoundException(
                    source_id=str(source_id),
                    details="No current revision found for source"
                )

            revision_data = {
                "kind": current_revision.kind,
                "title": current_revision.title,
                "authors": current_revision.authors,
                "year": current_revision.year,
                "origin": current_revision.origin,
                "url": current_revision.url,
                "trust_level": current_revision.trust_level,
                "summary": current_revision.summary,
                "source_metadata": current_revision.source_metadata,
                "created_with_llm": current_revision.created_with_llm,
                "created_by_user_id": user_id or current_revision.created_by_user_id,
                "document_text": document_text,
                "document_format": document_format,
                "document_file_name": document_file_name,
                "document_extracted_at": datetime.now(timezone.utc),
            }

            await create_new_revision(
                db=self.db,
                revision_class=SourceRevision,
                parent_id_field="source_id",
                parent_id=source.id,
                revision_data=revision_data,
                set_as_current=True,
            )

            await self.db.commit()

        except SourceNotFoundException:
            raise
        except Exception as e:
            logger.error("Failed to add document to source %s: %s", source_id, e, exc_info=True)
            await self.db.rollback()
            raise

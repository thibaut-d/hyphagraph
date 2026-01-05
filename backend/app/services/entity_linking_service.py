"""
Entity linking service for matching extracted entities to existing ones.

Provides entity disambiguation and deduplication by finding matches
in the existing knowledge graph based on slugs and synonyms.
"""
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from dataclasses import dataclass

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.llm.schemas import ExtractedEntity

logger = logging.getLogger(__name__)


@dataclass
class EntityLinkMatch:
    """
    Represents a potential match between extracted entity and existing entity.
    """
    extracted_slug: str
    matched_entity_id: UUID | None
    matched_entity_slug: str | None
    confidence: float  # 0.0 - 1.0
    match_type: str  # "exact", "synonym", "similar", "none"


class EntityLinkingService:
    """
    Service for linking extracted entities to existing entities in the graph.

    Matches based on:
    1. Exact slug matches (confidence=1.0)
    2. Synonym matches via entity_terms table (confidence=0.8)
    3. Similar slug matches (confidence=0.6) - future enhancement

    Auto-links matches with confidence >= threshold (default 0.8).
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize entity linking service.

        Args:
            db: Database session for querying entities
        """
        self.db = db

    async def find_entity_matches(
        self,
        extracted_entities: list[ExtractedEntity]
    ) -> list[EntityLinkMatch]:
        """
        Find potential matches for extracted entities in the existing graph.

        Checks:
        1. Exact slug matches in entity_revisions (is_current=True)
        2. Synonym matches in entity_terms table

        Args:
            extracted_entities: List of entities extracted from document

        Returns:
            List of EntityLinkMatch with confidence scores
        """
        matches = []

        for extracted in extracted_entities:
            # Try exact slug match first
            exact_match = await self._find_exact_slug_match(extracted.slug)

            if exact_match:
                matches.append(EntityLinkMatch(
                    extracted_slug=extracted.slug,
                    matched_entity_id=exact_match["entity_id"],
                    matched_entity_slug=exact_match["slug"],
                    confidence=1.0,
                    match_type="exact"
                ))
                continue

            # Try synonym match via entity_terms
            synonym_match = await self._find_synonym_match(extracted.slug)

            if synonym_match:
                matches.append(EntityLinkMatch(
                    extracted_slug=extracted.slug,
                    matched_entity_id=synonym_match["entity_id"],
                    matched_entity_slug=synonym_match["entity_slug"],
                    confidence=0.8,
                    match_type="synonym"
                ))
                continue

            # No match found - will create new entity
            matches.append(EntityLinkMatch(
                extracted_slug=extracted.slug,
                matched_entity_id=None,
                matched_entity_slug=None,
                confidence=0.0,
                match_type="none"
            ))

        logger.info(
            f"Entity linking: {len(extracted_entities)} entities, "
            f"{sum(1 for m in matches if m.match_type == 'exact')} exact matches, "
            f"{sum(1 for m in matches if m.match_type == 'synonym')} synonym matches"
        )

        return matches

    async def _find_exact_slug_match(self, slug: str) -> dict | None:
        """
        Find entity with exact slug match in current revisions.

        Args:
            slug: Entity slug to search for

        Returns:
            Dict with entity_id and slug if found, None otherwise
        """
        stmt = (
            select(Entity.id, EntityRevision.slug)
            .join(EntityRevision, EntityRevision.entity_id == Entity.id)
            .where(
                and_(
                    EntityRevision.slug == slug,
                    EntityRevision.is_current == True
                )
            )
            .limit(1)
        )

        result = await self.db.execute(stmt)
        row = result.first()

        if row:
            return {
                "entity_id": row[0],
                "slug": row[1]
            }

        return None

    async def _find_synonym_match(self, term: str) -> dict | None:
        """
        Find entity with matching term in entity_terms table.

        Args:
            term: Term to search for in entity synonyms

        Returns:
            Dict with entity_id and entity_slug if found, None otherwise
        """
        # Find entity_term matching the term
        stmt = (
            select(
                EntityTerm.entity_id,
                EntityRevision.slug
            )
            .join(Entity, Entity.id == EntityTerm.entity_id)
            .join(EntityRevision, EntityRevision.entity_id == Entity.id)
            .where(
                and_(
                    EntityTerm.term == term,
                    EntityRevision.is_current == True
                )
            )
            .limit(1)
        )

        result = await self.db.execute(stmt)
        row = result.first()

        if row:
            return {
                "entity_id": row[0],
                "entity_slug": row[1]
            }

        return None

    def filter_high_confidence(
        self,
        matches: list[EntityLinkMatch],
        threshold: float = 0.8
    ) -> dict[str, UUID]:
        """
        Filter matches above confidence threshold for auto-linking.

        Args:
            matches: List of entity matches
            threshold: Minimum confidence for auto-link (default 0.8)

        Returns:
            Dict mapping extracted_slug -> existing entity_id for auto-linkable matches
        """
        auto_links = {}

        for match in matches:
            if match.confidence >= threshold and match.matched_entity_id:
                auto_links[match.extracted_slug] = match.matched_entity_id

        logger.info(f"Auto-linking {len(auto_links)} entities with confidence >= {threshold}")

        return auto_links

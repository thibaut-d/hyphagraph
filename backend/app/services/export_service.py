"""
Export service for entities, relations, and sources.

Supports multiple formats:
- JSON: Complete graph export with all metadata
- CSV: Tabular format for spreadsheet analysis
- RDF/Turtle: Semantic web format for knowledge graph interoperability
"""
import json
import csv
from io import StringIO
from datetime import datetime
from typing import Any, List, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from sqlalchemy import String, and_, case, cast, distinct, func, or_, select

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.ui_category import UiCategory
from app.schemas.filters import SourceFilters
from app.schemas.export import EntityExportItem, RelationExportItem, RelationRoleExportItem, SourceExportItem
from app.services.query_predicates import canonical_relation_predicate
from app.services.source_service import DOMAIN_KEYWORDS


ExportFormat = Literal["json", "csv", "rdf"]


def _escape_turtle_string(s: str) -> str:
    """Escape a string for use as an RDF/Turtle string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")


class ExportService:
    """Service for exporting knowledge graph data in various formats."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _build_filtered_source_query(self, filters: SourceFilters | None = None):
        query = (
            select(Source, SourceRevision)
            .join(SourceRevision, Source.id == SourceRevision.source_id)
            .where(SourceRevision.is_current == True)
            .where(SourceRevision.status == "confirmed")
        )

        if not filters:
            return query

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

        if filters.domain:
            domain_conditions = []
            for domain in filters.domain:
                keyword_conditions = []
                for keyword in DOMAIN_KEYWORDS.get(domain, []):
                    keyword_pattern = f"%{keyword}%"
                    keyword_conditions.append(
                        or_(
                            SourceRevision.origin.ilike(keyword_pattern),
                            SourceRevision.title.ilike(keyword_pattern),
                        )
                    )
                if keyword_conditions:
                    domain_conditions.append(or_(*keyword_conditions))
            if domain_conditions:
                query = query.where(or_(*domain_conditions))

        if filters.role:
            relation_stats = (
                select(
                    Relation.source_id.label("source_id"),
                    func.count(distinct(Relation.id)).label("relation_count"),
                    func.sum(
                        case((RelationRevision.direction == "contradicts", 1), else_=0)
                    ).label("contradictory_count"),
                )
                .join(RelationRevision, Relation.id == RelationRevision.relation_id)
                .where(canonical_relation_predicate())
                .group_by(Relation.source_id)
                .subquery()
            )
            query = query.join(relation_stats, Source.id == relation_stats.c.source_id, isouter=True)

            role_conditions = []
            if "pillar" in filters.role:
                role_conditions.append(relation_stats.c.relation_count > 5)
            if "supporting" in filters.role:
                role_conditions.append(
                    and_(
                        relation_stats.c.relation_count >= 2,
                        relation_stats.c.relation_count <= 5,
                    )
                )
            if "contradictory" in filters.role:
                role_conditions.append(relation_stats.c.contradictory_count > 0)
            if "single" in filters.role:
                role_conditions.append(relation_stats.c.relation_count == 1)
            if role_conditions:
                query = query.where(or_(*role_conditions))

        return query

    def _serialize_source_row(
        self,
        source: Source,
        revision: SourceRevision,
        *,
        include_metadata: bool,
        include_source_metadata: bool = False,
    ) -> SourceExportItem:
        item = SourceExportItem(
            id=str(source.id),
            kind=revision.kind,
            title=revision.title,
            authors=revision.authors,
            year=revision.year,
            origin=revision.origin,
            url=revision.url,
            trust_level=revision.trust_level,
            calculated_trust_level=revision.calculated_trust_level,
            status=revision.status,
            summary_en=(revision.summary or {}).get("en"),
            summary_fr=(revision.summary or {}).get("fr"),
            source_metadata=revision.source_metadata if include_source_metadata else None,
        )
        if include_metadata:
            item.created_at = source.created_at.isoformat() if source.created_at else None
            item.revision_created_at = revision.created_at.isoformat() if revision.created_at else None
            item.created_by_user_id = str(revision.created_by_user_id) if revision.created_by_user_id else None
            item.created_with_llm = revision.created_with_llm
            item.llm_review_status = revision.llm_review_status
        return item

    def _build_export_payload(self, export_type: str, key: str, items: list[dict[str, Any]]) -> str:
        return json.dumps(
            {
                "export_type": export_type,
                "export_date": datetime.utcnow().isoformat(),
                "count": len(items),
                key: items,
            },
            indent=2,
            ensure_ascii=False,
        )

    async def _load_entity_export_items(
        self,
        *,
        include_metadata: bool,
    ) -> list[EntityExportItem]:
        stmt = (
            select(Entity, EntityRevision, UiCategory.slug.label("category_slug"))
            .join(EntityRevision, Entity.id == EntityRevision.entity_id)
            .outerjoin(UiCategory, EntityRevision.ui_category_id == UiCategory.id)
            .where(EntityRevision.is_current == True)
            .where(Entity.is_rejected == False)
            .where(Entity.is_merged == False)  # NEW-MRG-M1
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # Bulk-load all EntityTerms for these entities in one query
        entity_ids = [entity.id for entity, _, _ in rows]
        terms_by_entity: dict[object, list[EntityTerm]] = defaultdict(list)
        if entity_ids:
            terms_result = await self.db.execute(
                select(EntityTerm)
                .where(EntityTerm.entity_id.in_(entity_ids))
                .order_by(EntityTerm.entity_id, EntityTerm.display_order)
            )
            for (term,) in terms_result:
                terms_by_entity[term.entity_id].append(term)

        items: list[EntityExportItem] = []
        for entity, revision, category_slug in rows:
            summary = revision.summary or {}

            # Build display names and aliases from terms
            display_name: str | None = None
            display_name_en: str | None = None
            display_name_fr: str | None = None
            alias_parts: list[str] = []
            for term in terms_by_entity.get(entity.id, []):
                if term.is_display_name:
                    if term.language is None:
                        display_name = term.term
                    elif term.language == "en":
                        display_name_en = term.term
                    elif term.language == "fr":
                        display_name_fr = term.term
                else:
                    lang_suffix = f":{term.language}" if term.language else ":"
                    alias_parts.append(f"{term.term}{lang_suffix}")

            item = EntityExportItem(
                id=str(entity.id),
                slug=revision.slug,
                ui_category_slug=category_slug,
                display_name=display_name,
                display_name_en=display_name_en,
                display_name_fr=display_name_fr,
                summary_en=summary.get("en"),
                summary_fr=summary.get("fr"),
                aliases=";".join(alias_parts) if alias_parts else None,
                status=revision.status,
                ui_category_id=str(revision.ui_category_id) if revision.ui_category_id else None,
            )
            if include_metadata:
                item.created_at = entity.created_at.isoformat() if entity.created_at else None
                item.revision_created_at = revision.created_at.isoformat() if revision.created_at else None
                item.created_with_llm = revision.created_with_llm
                item.created_by_user_id = (
                    str(revision.created_by_user_id) if revision.created_by_user_id else None
                )
                item.llm_review_status = revision.llm_review_status
            items.append(item)
        return items

    async def _load_source_export_items(
        self,
        *,
        include_metadata: bool,
        include_source_metadata: bool = False,
        filters: SourceFilters | None = None,
    ) -> list[SourceExportItem]:
        result = await self.db.execute(self._build_filtered_source_query(filters))
        return [
            self._serialize_source_row(
                source,
                revision,
                include_metadata=include_metadata,
                include_source_metadata=include_source_metadata,
            )
            for source, revision in result
        ]

    async def _load_relation_export_items(
        self,
        *,
        include_metadata: bool,
        filters: SourceFilters,
    ) -> list[RelationExportItem]:
        filtered_sources = self._build_filtered_source_query(filters).subquery()
        stmt = (
            select(Relation, RelationRevision, SourceRevision)
            .join(RelationRevision, Relation.id == RelationRevision.relation_id)
            .join(filtered_sources, Relation.source_id == filtered_sources.c.id)
            .join(SourceRevision, SourceRevision.source_id == Relation.source_id)
            .where(canonical_relation_predicate())
            .where(SourceRevision.is_current == True)
            .where(SourceRevision.status == "confirmed")
        )

        result = await self.db.execute(stmt)
        relation_rows = result.all()
        relation_revision_ids = [row[1].id for row in relation_rows]
        roles_by_revision_id = await self._load_relation_roles_by_revision_id(relation_revision_ids)

        items: list[RelationExportItem] = []
        for relation, rel_revision, source_revision in relation_rows:
            item = RelationExportItem(
                id=str(relation.id),
                kind=rel_revision.kind,
                direction=rel_revision.direction,
                confidence=rel_revision.confidence,
                status=rel_revision.status,
                source_id=str(relation.source_id),
                source_title=source_revision.title,
                roles=roles_by_revision_id.get(rel_revision.id, []),
            )
            if include_metadata:
                item.created_at = relation.created_at.isoformat() if relation.created_at else None
                item.revision_created_at = (
                    rel_revision.created_at.isoformat() if rel_revision.created_at else None
                )
                item.scope = rel_revision.scope
                item.notes = rel_revision.notes
                item.created_with_llm = rel_revision.created_with_llm
                item.created_by_user_id = (
                    str(rel_revision.created_by_user_id) if rel_revision.created_by_user_id else None
                )
                item.llm_review_status = rel_revision.llm_review_status
            items.append(item)
        return items

    async def _load_relation_roles_by_revision_id(
        self,
        relation_revision_ids: list[object],
    ) -> dict[object, list[RelationRoleExportItem]]:
        roles_by_revision_id: dict[object, list[RelationRoleExportItem]] = defaultdict(list)
        if not relation_revision_ids:
            return roles_by_revision_id

        roles_stmt = (
            select(RelationRoleRevision, EntityRevision)
            .join(EntityRevision, RelationRoleRevision.entity_id == EntityRevision.entity_id)
            .where(RelationRoleRevision.relation_revision_id.in_(relation_revision_ids))
            .where(EntityRevision.is_current == True)
            .where(EntityRevision.status == "confirmed")
        )
        roles_result = await self.db.execute(roles_stmt)
        for role_rev, entity_rev in roles_result:
            roles_by_revision_id[role_rev.relation_revision_id].append(
                RelationRoleExportItem(
                    entity_slug=entity_rev.slug,
                    entity_id=str(role_rev.entity_id),
                    role_type=role_rev.role_type,
                    weight=role_rev.weight,
                    coverage=role_rev.coverage,
                )
            )

        return roles_by_revision_id

    # =========================================================================
    # ENTITIES EXPORT
    # =========================================================================

    async def export_entities(
        self,
        format: ExportFormat = "json",
        include_metadata: bool = True
    ) -> str:
        """
        Export all entities in specified format.

        Args:
            format: Output format (json, csv, rdf)
            include_metadata: Include creation dates, user IDs, etc.

        Returns:
            Formatted string ready for download
        """
        entities_data = await self._load_entity_export_items(include_metadata=include_metadata)

        # Format output
        if format == "json":
            return self._export_entities_json(entities_data)
        elif format == "csv":
            return self._export_entities_csv(entities_data)
        elif format == "rdf":
            return self._export_entities_rdf(entities_data)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_entities_json(self, entities: List[EntityExportItem]) -> str:
        """Export entities as JSON."""
        return self._build_export_payload(
            "entities",
            "entities",
            [entity.model_dump(exclude_none=True) for entity in entities],
        )

    def _export_entities_csv(self, entities: List[EntityExportItem]) -> str:
        """Export entities as CSV."""
        if not entities:
            return "slug,ui_category_slug,display_name,display_name_en,display_name_fr,summary_en,summary_fr,aliases\n"

        output = StringIO()
        writer = csv.writer(output)

        # Header — import-compatible columns first, metadata at end
        writer.writerow([
            'slug', 'ui_category_slug', 'display_name', 'display_name_en', 'display_name_fr',
            'summary_en', 'summary_fr', 'aliases',
            'id', 'created_at', 'created_with_llm',
        ])

        # Rows
        for entity in entities:
            writer.writerow([
                entity.slug,
                entity.ui_category_slug or '',
                entity.display_name or '',
                entity.display_name_en or '',
                entity.display_name_fr or '',
                entity.summary_en or '',
                entity.summary_fr or '',
                entity.aliases or '',
                entity.id,
                entity.created_at or '',
                entity.created_with_llm if entity.created_with_llm is not None else '',
            ])

        return output.getvalue()

    def _export_entities_rdf(self, entities: List[EntityExportItem]) -> str:
        """Export entities as RDF Turtle format."""
        lines = [
            "@prefix hypha: <http://hyphagraph.org/entity/> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix dc: <http://purl.org/dc/terms/> .",
            "",
        ]

        for entity in entities:
            lines.append(f"hypha:{entity.slug} a hypha:Entity ;")
            lines.append(f'    rdfs:label "{_escape_turtle_string(entity.slug)}" ;')

            if entity.summary_en:
                lines.append(f'    rdfs:comment "{_escape_turtle_string(entity.summary_en)}"@en ;')
            if entity.summary_fr:
                lines.append(f'    rdfs:comment "{_escape_turtle_string(entity.summary_fr)}"@fr ;')

            lines.append(f'    dc:identifier "{entity.id}" ;')

            if entity.created_at:
                lines.append(f'    dc:created "{entity.created_at}"^^xsd:dateTime ;')

            lines.append("    .")
            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # RELATIONS EXPORT
    # =========================================================================

    async def export_relations(
        self,
        format: ExportFormat = "json",
        include_metadata: bool = True,
        kind: list[str] | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        trust_level_min: float | None = None,
        trust_level_max: float | None = None,
        search: str | None = None,
        domain: list[str] | None = None,
        role: list[str] | None = None,
    ) -> str:
        """Export all relations with their roles."""
        filters = SourceFilters(
            kind=kind,
            year_min=year_min,
            year_max=year_max,
            trust_level_min=trust_level_min,
            trust_level_max=trust_level_max,
            search=search,
            domain=domain,
            role=role,
        )
        relations_data = await self._load_relation_export_items(
            include_metadata=include_metadata,
            filters=filters,
        )

        # Format output
        if format == "json":
            return self._export_relations_json(relations_data)
        elif format == "csv":
            return self._export_relations_csv(relations_data)
        elif format == "rdf":
            return self._export_relations_rdf(relations_data)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_relations_json(self, relations: List[RelationExportItem]) -> str:
        """Export relations as JSON."""
        return self._build_export_payload(
            "relations",
            "relations",
            [relation.model_dump(exclude_none=True) for relation in relations],
        )

    def _export_relations_csv(self, relations: List[RelationExportItem]) -> str:
        """Export relations as CSV (flattened)."""
        if not relations:
            return "id,kind,direction,confidence,source_id,source_title,created_at,roles_json\n"

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'id', 'kind', 'direction', 'confidence', 'source_id', 'source_title',
            'created_at', 'roles_json'
        ])

        for relation in relations:
            roles_json = json.dumps([
                {'entity_slug': r.entity_slug, 'role_type': r.role_type}
                for r in relation.roles
            ])
            writer.writerow([
                relation.id,
                relation.kind or '',
                relation.direction or '',
                relation.confidence,
                relation.source_id,
                relation.source_title or '',
                relation.created_at or '',
                roles_json,
            ])

        return output.getvalue()

    def _export_relations_rdf(self, relations: List[RelationExportItem]) -> str:
        """Export relations as RDF Turtle format."""
        lines = [
            "@prefix hypha: <http://hyphagraph.org/> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix dc: <http://purl.org/dc/terms/> .",
            "",
        ]

        for relation in relations:
            subject = next((r for r in relation.roles if r.role_type == 'subject'), None)
            obj = next((r for r in relation.roles if r.role_type == 'object'), None)

            if subject and obj:
                lines.append(f"hypha:{subject.entity_slug} hypha:{relation.kind} hypha:{obj.entity_slug} ;")
                lines.append(f'    dc:relation "{_escape_turtle_string(relation.id)}" ;')
                lines.append(f'    hypha:direction "{_escape_turtle_string(relation.direction or "")}" ;')
                lines.append(f'    hypha:confidence {relation.confidence} ;')
                lines.append(f'    dc:source hypha:source/{relation.source_id} ;')
                lines.append("    .")
                lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # SOURCES EXPORT
    # =========================================================================

    async def export_sources(
        self,
        format: ExportFormat = "json",
        include_metadata: bool = True,
        kind: list[str] | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        trust_level_min: float | None = None,
        trust_level_max: float | None = None,
        search: str | None = None,
        domain: list[str] | None = None,
        role: list[str] | None = None,
    ) -> str:
        """Export sources in JSON or CSV format, respecting the same filters as the list endpoint."""
        filters = SourceFilters(
            kind=kind,
            year_min=year_min,
            year_max=year_max,
            trust_level_min=trust_level_min,
            trust_level_max=trust_level_max,
            search=search,
            domain=domain,
            role=role,
        )
        sources_data = await self._load_source_export_items(
            include_metadata=include_metadata,
            filters=filters,
        )

        if format == "json":
            return self._build_export_payload(
                "sources",
                "sources",
                [source.model_dump(exclude_none=True) for source in sources_data],
            )
        elif format == "csv":
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "kind", "title", "authors", "year", "origin", "url", "trust_level", "created_at"])
            for s in sources_data:
                authors = s.authors or []
                writer.writerow([
                    s.id,
                    s.kind or '',
                    s.title or '',
                    "; ".join(authors) if isinstance(authors, list) else str(authors),
                    s.year or '',
                    s.origin or '',
                    s.url or '',
                    s.trust_level if s.trust_level is not None else '',
                    s.created_at or '',
                ])
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format for sources export: {format}")

    # =========================================================================
    # FULL GRAPH EXPORT
    # =========================================================================

    async def export_full_graph(
        self,
        format: ExportFormat = "json",
        include_metadata: bool = True
    ) -> str:
        """
        Export complete knowledge graph (entities + relations + sources).

        This creates a complete, self-contained export that can be
        reimported into another HyphaGraph instance.
        """
        if format != "json":
            # CSV and RDF don't support full graph in single file
            raise ValueError("Full graph export only supports JSON format")

        entities_data = await self._load_entity_export_items(include_metadata=include_metadata)
        relations_data = await self._load_relation_export_items(
            include_metadata=include_metadata,
            filters=SourceFilters(),
        )
        sources_data = await self._load_source_export_items(
            include_metadata=include_metadata,
            include_source_metadata=True,
            filters=None,
        )

        # Combine all
        return json.dumps({
            'export_type': 'full_graph',
            'export_date': datetime.utcnow().isoformat(),
            'metadata': {
                'entity_count': len(entities_data),
                'relation_count': len(relations_data),
                'source_count': len(sources_data),
            },
            'entities': [entity.model_dump(exclude_none=True) for entity in entities_data],
            'relations': [relation.model_dump(exclude_none=True) for relation in relations_data],
            'sources': [s.model_dump(exclude_none=True) for s in sources_data],
        }, indent=2, ensure_ascii=False)

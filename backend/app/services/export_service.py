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
from typing import List, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision


ExportFormat = Literal["json", "csv", "rdf"]


class ExportService:
    """Service for exporting knowledge graph data in various formats."""

    def __init__(self, db: AsyncSession):
        self.db = db

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
        # Fetch all current entities
        stmt = select(Entity, EntityRevision).join(
            EntityRevision, Entity.id == EntityRevision.entity_id
        ).where(EntityRevision.is_current == True)

        result = await self.db.execute(stmt)
        entities_data = []

        for entity, revision in result:
            entity_dict = {
                'id': str(entity.id),
                'slug': revision.slug,
                'summary': revision.summary,
                'ui_category_id': str(revision.ui_category_id) if revision.ui_category_id else None,
            }

            if include_metadata:
                entity_dict.update({
                    'created_at': entity.created_at.isoformat() if entity.created_at else None,
                    'created_with_llm': revision.created_with_llm,
                    'created_by_user_id': str(revision.created_by_user_id) if revision.created_by_user_id else None,
                })

            entities_data.append(entity_dict)

        # Format output
        if format == "json":
            return self._export_entities_json(entities_data)
        elif format == "csv":
            return self._export_entities_csv(entities_data)
        elif format == "rdf":
            return self._export_entities_rdf(entities_data)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_entities_json(self, entities: List[dict]) -> str:
        """Export entities as JSON."""
        return json.dumps({
            'export_type': 'entities',
            'export_date': datetime.utcnow().isoformat(),
            'count': len(entities),
            'entities': entities
        }, indent=2, ensure_ascii=False)

    def _export_entities_csv(self, entities: List[dict]) -> str:
        """Export entities as CSV."""
        if not entities:
            return "id,slug,summary_en,summary_fr,ui_category_id,created_at\n"

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['id', 'slug', 'summary_en', 'summary_fr', 'ui_category_id', 'created_at', 'created_with_llm'])

        # Rows
        for entity in entities:
            summary = entity.get('summary', {}) or {}
            writer.writerow([
                entity['id'],
                entity['slug'],
                summary.get('en', ''),
                summary.get('fr', ''),
                entity.get('ui_category_id', ''),
                entity.get('created_at', ''),
                entity.get('created_with_llm', '')
            ])

        return output.getvalue()

    def _export_entities_rdf(self, entities: List[dict]) -> str:
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
            slug = entity['slug']
            entity_id = entity['id']
            summary = entity.get('summary', {}) or {}

            lines.append(f"hypha:{slug} a hypha:Entity ;")
            lines.append(f'    rdfs:label "{slug}" ;')

            if summary.get('en'):
                lines.append(f'    rdfs:comment "{summary["en"]}"@en ;')
            if summary.get('fr'):
                lines.append(f'    rdfs:comment "{summary["fr"]}"@fr ;')

            lines.append(f'    dc:identifier "{entity_id}" ;')

            if entity.get('created_at'):
                lines.append(f'    dc:created "{entity["created_at"]}"^^xsd:dateTime ;')

            lines.append("    .")
            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # RELATIONS EXPORT
    # =========================================================================

    async def export_relations(
        self,
        format: ExportFormat = "json",
        include_metadata: bool = True
    ) -> str:
        """Export all relations with their roles."""
        # Fetch all current relations with roles
        stmt = select(Relation, RelationRevision, Source, SourceRevision).join(
            RelationRevision, Relation.id == RelationRevision.relation_id
        ).join(
            Source, Relation.source_id == Source.id
        ).join(
            SourceRevision, Source.id == SourceRevision.source_id
        ).where(
            RelationRevision.is_current == True,
            SourceRevision.is_current == True
        )

        result = await self.db.execute(stmt)
        relations_data = []

        for relation, rel_revision, source, source_revision in result:
            # Get roles
            roles_stmt = select(RelationRoleRevision, EntityRevision).join(
                EntityRevision, RelationRoleRevision.entity_id == EntityRevision.entity_id
            ).where(
                RelationRoleRevision.relation_revision_id == rel_revision.id,
                EntityRevision.is_current == True
            )

            roles_result = await self.db.execute(roles_stmt)
            roles = []

            for role_rev, entity_rev in roles_result:
                roles.append({
                    'entity_slug': entity_rev.slug,
                    'entity_id': str(role_rev.entity_id),
                    'role_type': role_rev.role_type,
                    'weight': role_rev.weight,
                    'coverage': role_rev.coverage
                })

            relation_dict = {
                'id': str(relation.id),
                'kind': rel_revision.kind,
                'direction': rel_revision.direction,
                'confidence': rel_revision.confidence,
                'source_id': str(relation.source_id),
                'source_title': source_revision.title,
                'roles': roles
            }

            if include_metadata:
                relation_dict.update({
                    'created_at': relation.created_at.isoformat() if relation.created_at else None,
                    'scope': rel_revision.scope,
                    'notes': rel_revision.notes,
                    'created_with_llm': rel_revision.created_with_llm,
                })

            relations_data.append(relation_dict)

        # Format output
        if format == "json":
            return self._export_relations_json(relations_data)
        elif format == "csv":
            return self._export_relations_csv(relations_data)
        elif format == "rdf":
            return self._export_relations_rdf(relations_data)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_relations_json(self, relations: List[dict]) -> str:
        """Export relations as JSON."""
        return json.dumps({
            'export_type': 'relations',
            'export_date': datetime.utcnow().isoformat(),
            'count': len(relations),
            'relations': relations
        }, indent=2, ensure_ascii=False)

    def _export_relations_csv(self, relations: List[dict]) -> str:
        """Export relations as CSV (flattened)."""
        if not relations:
            return "id,kind,direction,confidence,source_id,source_title,subject_slug,object_slug,created_at\n"

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'id', 'kind', 'direction', 'confidence', 'source_id', 'source_title',
            'subject_slug', 'object_slug', 'created_at'
        ])

        # Rows (assumes 2-role relations: subject/object)
        for relation in relations:
            roles = relation['roles']
            subject = next((r for r in roles if r['role_type'] == 'subject'), None)
            obj = next((r for r in roles if r['role_type'] == 'object'), None)

            writer.writerow([
                relation['id'],
                relation['kind'],
                relation['direction'],
                relation['confidence'],
                relation['source_id'],
                relation.get('source_title', ''),
                subject['entity_slug'] if subject else '',
                obj['entity_slug'] if obj else '',
                relation.get('created_at', '')
            ])

        return output.getvalue()

    def _export_relations_rdf(self, relations: List[dict]) -> str:
        """Export relations as RDF Turtle format."""
        lines = [
            "@prefix hypha: <http://hyphagraph.org/> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix dc: <http://purl.org/dc/terms/> .",
            "",
        ]

        for relation in relations:
            rel_id = relation['id']
            kind = relation['kind']
            direction = relation['direction']
            confidence = relation['confidence']

            roles = relation['roles']
            subject = next((r for r in roles if r['role_type'] == 'subject'), None)
            obj = next((r for r in roles if r['role_type'] == 'object'), None)

            if subject and obj:
                lines.append(f"hypha:{subject['entity_slug']} hypha:{kind} hypha:{obj['entity_slug']} ;")
                lines.append(f'    dc:relation "{rel_id}" ;')
                lines.append(f'    hypha:direction "{direction}" ;')
                lines.append(f'    hypha:confidence {confidence} ;')
                lines.append(f'    dc:source hypha:source/{relation["source_id"]} ;')
                lines.append("    .")
                lines.append("")

        return "\n".join(lines)

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

        # Get entities
        entities_json = await self.export_entities("json", include_metadata)
        entities_dict = json.loads(entities_json)

        # Get relations
        relations_json = await self.export_relations("json", include_metadata)
        relations_dict = json.loads(relations_json)

        # Get sources
        stmt = select(Source, SourceRevision).join(
            SourceRevision, Source.id == SourceRevision.source_id
        ).where(SourceRevision.is_current == True)

        result = await self.db.execute(stmt)
        sources_data = []

        for source, revision in result:
            source_dict = {
                'id': str(source.id),
                'kind': revision.kind,
                'title': revision.title,
                'authors': revision.authors,
                'year': revision.year,
                'origin': revision.origin,
                'url': revision.url,
                'trust_level': revision.trust_level,
                'summary': revision.summary,
                'source_metadata': revision.source_metadata,
            }

            if include_metadata:
                source_dict.update({
                    'created_at': source.created_at.isoformat() if source.created_at else None,
                    'created_with_llm': revision.created_with_llm,
                })

            sources_data.append(source_dict)

        # Combine all
        return json.dumps({
            'export_type': 'full_graph',
            'export_date': datetime.utcnow().isoformat(),
            'metadata': {
                'entity_count': entities_dict['count'],
                'relation_count': relations_dict['count'],
                'source_count': len(sources_data),
            },
            'entities': entities_dict['entities'],
            'relations': relations_dict['relations'],
            'sources': sources_data,
        }, indent=2, ensure_ascii=False)

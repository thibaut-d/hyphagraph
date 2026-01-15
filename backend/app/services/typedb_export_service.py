"""
TypeDB Export Service - Export HyphaGraph data to TypeDB TypeQL format.

Exports entities, relations, and semantic roles in TypeQL schema and data
format for import into TypeDB hypergraph database.

TypeDB: https://typedb.com/
TypeQL: https://github.com/typedb/typeql
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision


logger = logging.getLogger(__name__)


class TypeDBExportService:
    """Service for exporting knowledge graph to TypeDB TypeQL format."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_schema(self) -> str:
        """
        Generate TypeDB schema (TQL) from HyphaGraph model.

        Creates TypeQL schema definition with:
        - Entity types
        - Relation types with roles
        - Attributes
        """
        lines = [
            "# HyphaGraph Schema for TypeDB",
            "# Generated from PostgreSQL database",
            "",
            "define",
            "",
            "# ============================================================================",
            "# Entity Types",
            "# ============================================================================",
            "",
            "entity entity-node,",
            "    owns slug,",
            "    owns summary,",
            "    owns entity-id;",
            "",
            "# ============================================================================",
            "# Attributes",
            "# ============================================================================",
            "",
            "slug sub attribute, value string;",
            "summary sub attribute, value string;",
            "entity-id sub attribute, value string;",
            "confidence sub attribute, value double;",
            "source-title sub attribute, value string;",
            "source-pmid sub attribute, value string;",
            "",
            "# ============================================================================",
            "# Relation Types with Semantic Roles",
            "# ============================================================================",
        ]

        # Get relation types from database
        from app.services.relation_type_service import RelationTypeService
        rel_service = RelationTypeService(self.db)
        relation_types = await rel_service.get_all_active()

        # Get semantic role types
        from app.services.semantic_role_service import SemanticRoleService
        role_service = SemanticRoleService(self.db)
        semantic_roles = await role_service.get_all_active()

        # For each relation type, create TypeDB relation with dynamic roles
        for rel_type in relation_types:
            type_id = rel_type.type_id.replace('_', '-')  # TypeDB uses hyphens

            lines.append("")
            lines.append(f"# {rel_type.description}")
            lines.append(f"{type_id} sub relation,")

            # Add all semantic roles as possible role players
            role_definitions = []
            for role in semantic_roles:
                role_name = role['role_type'].replace('_', '-')
                role_definitions.append(f"    relates {role_name}")

            lines.append(",\n".join(role_definitions) + ",")
            lines.append("    owns confidence;")

        lines.append("")
        return "\n".join(lines)

    async def export_data(self, limit: int = None) -> str:
        """
        Generate TypeDB data insertion script (TypeQL).

        Exports all entities and relations in TypeQL insert format.

        Args:
            limit: Optional limit on number of entities to export

        Returns:
            TypeQL insert statements
        """
        lines = [
            "# HyphaGraph Data for TypeDB",
            "# Generated from PostgreSQL database",
            "",
        ]

        # Export entities
        stmt = select(Entity, EntityRevision).join(
            EntityRevision, Entity.id == EntityRevision.entity_id
        ).where(EntityRevision.is_current == True)

        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        entity_count = 0

        lines.append("# ============================================================================")
        lines.append("# Entities")
        lines.append("# ============================================================================")
        lines.append("")

        for entity, revision in result:
            entity_count += 1
            slug = revision.slug
            summary = revision.summary

            # Get English summary if available
            summary_text = ""
            if summary:
                if isinstance(summary, dict):
                    summary_text = summary.get('en', str(summary))
                elif isinstance(summary, str):
                    import json
                    try:
                        summary_dict = json.loads(summary)
                        summary_text = summary_dict.get('en', summary)
                    except:
                        summary_text = summary

            # Escape quotes for TypeQL
            summary_text = summary_text.replace('"', '\\"').replace("'", "\\'")

            lines.append("insert")
            lines.append(f"$e isa entity-node,")
            lines.append(f'    has slug "{slug}",')
            if summary_text:
                lines.append(f'    has summary "{summary_text[:200]}",')
            lines.append(f'    has entity-id "{entity.id}";')
            lines.append("")

        # Export relations with semantic roles
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

        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)

        lines.append("# ============================================================================")
        lines.append("# Relations with Semantic Roles")
        lines.append("# ============================================================================")
        lines.append("")

        relation_count = 0

        for relation, rel_revision, source, source_revision in result:
            relation_count += 1

            # Get roles for this relation
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
                    'role_type': role_rev.role_type,
                    'entity_id': role_rev.entity_id
                })

            # Generate TypeQL insert for this relation
            relation_type = rel_revision.kind.replace('_', '-')
            confidence = rel_revision.confidence or 0.8

            lines.append("insert")
            lines.append(f"$r isa {relation_type},")

            # Add role players
            for idx, role in enumerate(roles):
                var_name = f"e{idx}"
                role_name = role['role_type'].replace('_', '-')
                slug = role['entity_slug']

                lines.append(f'    has {role_name} $r-{var_name};')
                lines.append(f'$r-{var_name} isa entity-node, has slug "{slug}";')

            lines.append(f"    has confidence {confidence};")
            lines.append("")

        lines.append("")
        lines.append(f"# Exported {entity_count} entities and {relation_count} relations")

        return "\n".join(lines)

    async def export_full(self) -> dict:
        """
        Generate complete TypeDB export (schema + data).

        Returns:
            Dict with 'schema' and 'data' keys containing TypeQL scripts
        """
        schema = await self.export_schema()
        data = await self.export_data()

        return {
            'schema': schema,
            'data': data,
            'format': 'typeql',
            'database': 'typedb',
            'version': '3.0'
        }

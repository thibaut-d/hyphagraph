from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.config import settings
from app.models.base import Base

# Import ALL models so Alembic sees them
# Base tables
from app.models.entity import Entity
from app.models.source import Source
from app.models.relation import Relation
from app.models.user import User

# Revision tables
from app.models.entity_revision import EntityRevision
from app.models.source_revision import SourceRevision
from app.models.relation_revision import RelationRevision

# Supporting tables
from app.models.ui_category import UiCategory
from app.models.entity_term import EntityTerm
from app.models.attribute import Attribute
from app.models.relation_role_revision import RelationRoleRevision
from app.models.computed_relation import ComputedRelation

# Legacy tables (backward compatibility)
from app.models.role import Role
from app.models.inference_cache import InferenceCache


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        {
            "sqlalchemy.url": settings.DATABASE_URL,
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def do_run_migrations(connection: Connection) -> None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    import asyncio
    asyncio.run(
        connectable.connect().run_sync(do_run_migrations)
    )


run_migrations_online()
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    auth,
    document_extraction,
    entities,
    entity_terms,
    explain,
    export,
    extraction,
    extraction_review,
    inferences,
    relations,
    relation_types,
    search,
    sources,
    users,
)
from app.config import settings
from app.database import AsyncSessionLocal
from app.middleware.error_handler import register_error_handlers
from app.startup import run_startup_tasks
from app.utils.rate_limit import limiter

# Import all models to ensure SQLAlchemy discovers all tables and relationships
# This prevents NoReferencedTableError during foreign key resolution
from app.models.entity import Entity
from app.models.entity_merge_record import EntityMergeRecord
from app.models.source import Source
from app.models.relation import Relation
from app.models.user import User
from app.models.entity_revision import EntityRevision
from app.models.source_revision import SourceRevision
from app.models.relation_revision import RelationRevision
from app.models.ui_category import UiCategory
from app.models.entity_term import EntityTerm
from app.models.attribute import Attribute
from app.models.relation_role_revision import RelationRoleRevision
from app.models.computed_relation import ComputedRelation
from app.models.refresh_token import RefreshToken
from app.models.audit_log import AuditLog
from app.models.relation_type import RelationType
from app.models.staged_extraction import StagedExtraction


def _load_test_helpers_router():
    """
    Load the testing-only helper router.

    The router is only available in TESTING mode, so the import stays behind
    this helper instead of leaking test-only modules into normal runtime startup.
    """
    from app.api import test_helpers

    return test_helpers.router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Runs startup tasks when the application starts,
    and cleanup tasks when it shuts down.
    """
    # Startup: Create admin user and run other initialization tasks
    async with AsyncSessionLocal() as db:
        await run_startup_tasks(db)

    yield

    # Shutdown: Add cleanup tasks here if needed in the future


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.ENV == "development",
    lifespan=lifespan,
)

# --- Error Handling ---
register_error_handlers(app)

# --- Rate Limiting ---
app.state.limiter = limiter

# --- CORS (dev only; safe behind Caddy) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers (all under /api) ---
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(entities.router, prefix="/api/entities", tags=["entities"])
app.include_router(entity_terms.router, prefix="/api/entities", tags=["entity-terms"])
app.include_router(relations.router, prefix="/api/relations", tags=["relations"])
app.include_router(inferences.router, prefix="/api/inferences", tags=["inferences"])
app.include_router(explain.router, prefix="/api/explain", tags=["explain"])
app.include_router(search.router, prefix="/api")
app.include_router(extraction.router, prefix="/api")
app.include_router(document_extraction.router, prefix="/api")
app.include_router(relation_types.router, prefix="/api/relation-types", tags=["relation-types"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(extraction_review.router, prefix="/api")

# --- Test Helpers (only in testing mode) ---
if settings.TESTING:
    app.include_router(_load_test_helpers_router(), prefix="/api")

# --- Healthcheck ---
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}

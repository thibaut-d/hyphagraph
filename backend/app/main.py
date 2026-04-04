import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    auth,
    bug_reports,
    document_extraction,
    entities,
    entity_terms,
    explain,
    export,
    extraction,
    extraction_review,
    import_routes,
    inferences,
    relations,
    relation_types,
    revision_review,
    search,
    sources,
    users,
)
from app.config import settings
from app.database import AsyncSessionLocal
from app.middleware.error_handler import register_error_handlers
from app.services.user.tokens import purge_expired_tokens
from app.startup import run_startup_tasks
from app.utils.rate_limit import limiter

_logger = logging.getLogger(__name__)
_PURGE_INTERVAL_SECONDS = 24 * 60 * 60  # 24 hours
_PURGE_CRITICAL_THRESHOLD = 5
_TOKEN_PURGE_FAILURE_THRESHOLD = 3
_consecutive_token_purge_failures = 0


def _record_token_purge_success() -> None:
    global _consecutive_token_purge_failures
    _consecutive_token_purge_failures = 0


def _record_token_purge_failure() -> None:
    global _consecutive_token_purge_failures
    _consecutive_token_purge_failures += 1
    if _consecutive_token_purge_failures >= _TOKEN_PURGE_FAILURE_THRESHOLD:
        _logger.critical(
            "Token purge has failed %d consecutive times",
            _consecutive_token_purge_failures,
        )


async def _token_purge_loop() -> None:
    """Background task: purge expired/revoked refresh tokens every 24 hours."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await purge_expired_tokens(db)
            _record_token_purge_success()
        except Exception:
            _record_token_purge_failure()
            _logger.exception("Token purge failed; will retry in %d s", _PURGE_INTERVAL_SECONDS)
        await asyncio.sleep(_PURGE_INTERVAL_SECONDS)

# Import all models to ensure SQLAlchemy discovers all tables and relationships
# This prevents NoReferencedTableError during foreign key resolution
from app.models.entity import Entity  # noqa: F401
from app.models.entity_merge_record import EntityMergeRecord  # noqa: F401
from app.models.source import Source  # noqa: F401
from app.models.relation import Relation  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.entity_revision import EntityRevision  # noqa: F401
from app.models.source_revision import SourceRevision  # noqa: F401
from app.models.relation_revision import RelationRevision  # noqa: F401
from app.models.ui_category import UiCategory  # noqa: F401
from app.models.entity_term import EntityTerm  # noqa: F401
from app.models.attribute import Attribute  # noqa: F401
from app.models.relation_role_revision import RelationRoleRevision  # noqa: F401
from app.models.computed_relation import ComputedRelation  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.relation_type import RelationType  # noqa: F401
from app.models.staged_extraction import StagedExtraction  # noqa: F401
from app.models.bug_report import BugReport  # noqa: F401


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
    # Startup: initialization tasks
    async with AsyncSessionLocal() as db:
        await run_startup_tasks(db)

    # Background task: periodic refresh-token purge
    purge_task = asyncio.create_task(_token_purge_loop())

    yield

    # Shutdown: cancel background tasks
    purge_task.cancel()
    try:
        await purge_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.ENV == "development",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# --- Error Handling ---
register_error_handlers(app)

# --- Rate Limiting ---
app.state.limiter = limiter

# --- CORS — specific origins required when allow_credentials=True (cookies) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers (all under /api) ---
app.include_router(bug_reports.router, prefix="/api")
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
app.include_router(revision_review.router, prefix="/api")
app.include_router(import_routes.router, prefix="/api")

# --- Test Helpers (only in testing mode) ---
if settings.TESTING:
    app.include_router(_load_test_helpers_router(), prefix="/api")

# --- Healthcheck ---
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}

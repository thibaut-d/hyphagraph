from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api import sources, entities, relations, inferences, explain, search, extraction, document_extraction, relation_types, export
from app.database import AsyncSessionLocal
from app.startup import run_startup_tasks
from app.utils.rate_limit import limiter

# Import all models to ensure SQLAlchemy discovers all tables and relationships
# This prevents NoReferencedTableError during foreign key resolution
from app.models.entity import Entity
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

# --- Rate Limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS (dev only; safe behind Caddy) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers (all under /api) ---
from app.api import auth, users
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(entities.router, prefix="/api/entities", tags=["entities"])
app.include_router(relations.router, prefix="/api/relations", tags=["relations"])
app.include_router(inferences.router, prefix="/api/inferences", tags=["inferences"])
app.include_router(explain.router, prefix="/api/explain", tags=["explain"])
app.include_router(search.router, prefix="/api")
app.include_router(extraction.router, prefix="/api")
app.include_router(document_extraction.router, prefix="/api")
app.include_router(relation_types.router, prefix="/api/relation-types", tags=["relation-types"])
app.include_router(export.router, prefix="/api/export", tags=["export"])

# --- Healthcheck ---
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
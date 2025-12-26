from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api import sources, entities, relations, inferences, explain
from app.database import AsyncSessionLocal
from app.startup import run_startup_tasks
from app.utils.rate_limit import limiter


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

# --- Healthcheck ---
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
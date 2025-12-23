from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import sources, entities, relations, inferences, explain

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.ENV == "development",
)

# --- CORS (dev only; safe behind Caddy) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers (all under /api) ---
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(entities.router, prefix="/api/entities", tags=["entities"])
app.include_router(relations.router, prefix="/api/relations", tags=["relations"])
app.include_router(inferences.router, prefix="/api/inferences", tags=["inferences"])
app.include_router(explain.router, prefix="/api/explain", tags=["explain"])

# --- Healthcheck ---
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
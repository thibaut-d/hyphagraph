from fastapi import APIRouter
from app.api.document_extraction_routes.discovery import router as discovery_router
from app.api.document_extraction_routes.document import router as document_router

router = APIRouter(tags=["document-extraction"])
router.include_router(document_router)
router.include_router(discovery_router)

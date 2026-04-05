from fastapi import APIRouter, Depends, Query
from uuid import UUID

from app.api.service_dependencies import get_relation_service
from app.schemas.relation import RelationWrite, RelationRead
from app.schemas.pagination import PaginatedResponse
from app.services.relation_service import RelationService
from app.dependencies.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=RelationRead)
async def create_relation(
    payload: RelationWrite,
    service: RelationService = Depends(get_relation_service),
    user=Depends(get_current_user),  # 🔒 auth required
):
    return await service.create(payload, user_id=user.id if user else None)

@router.get("/", response_model=PaginatedResponse[RelationRead])
async def list_relations(
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    service: RelationService = Depends(get_relation_service),
):
    return await service.list_all(limit=limit, offset=offset)

@router.get("/by-source/{source_id}", response_model=list[RelationRead])
async def list_relations_by_source(
    source_id: UUID,
    service: RelationService = Depends(get_relation_service),
):
    # Intentionally unauthenticated: public read endpoint for source-scoped relations.
    return await service.list_by_source(source_id)

@router.get("/{relation_id}", response_model=RelationRead)
async def get_relation(
    relation_id: UUID,
    service: RelationService = Depends(get_relation_service),
):
    return await service.get(relation_id)

@router.put("/{relation_id}", response_model=RelationRead)
async def update_relation(
    relation_id: UUID,
    payload: RelationWrite,
    service: RelationService = Depends(get_relation_service),
    user=Depends(get_current_user),  # 🔒 auth required
):
    return await service.update(relation_id, payload, user_id=user.id if user else None)

@router.delete("/{relation_id}", status_code=204)
async def delete_relation(
    relation_id: UUID,
    service: RelationService = Depends(get_relation_service),
    user=Depends(get_current_user),  # 🔒 auth required
):
    await service.delete(relation_id)
    return None

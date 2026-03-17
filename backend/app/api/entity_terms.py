from fastapi import APIRouter, Depends
from uuid import UUID
from typing import List

from app.api.service_dependencies import get_entity_term_service
from app.schemas.entity_term import EntityTermWrite, EntityTermRead, EntityTermBulkWrite
from app.services.entity_term_service import EntityTermService
from app.dependencies.auth import get_current_user

router = APIRouter()


@router.get("/{entity_id}/terms", response_model=List[EntityTermRead])
async def list_entity_terms(
    entity_id: UUID,
    service: EntityTermService = Depends(get_entity_term_service),
):
    """
    Get all terms/aliases for a specific entity.

    Returns all terms ordered by display_order (nulls last), then by created_at.

    - **entity_id**: The entity UUID
    """
    return await service.list_by_entity(entity_id)


@router.post("/{entity_id}/terms", response_model=EntityTermRead, status_code=201)
async def create_entity_term(
    entity_id: UUID,
    payload: EntityTermWrite,
    service: EntityTermService = Depends(get_entity_term_service),
    user=Depends(get_current_user),
):
    """
    Add a new term/alias to an entity.

    Creates a new term for the specified entity. The term must be unique
    within the entity+language combination.

    - **entity_id**: The entity UUID
    - **term**: The term text (required)
    - **language**: ISO 639-1 language code (en, fr) or null for international terms
    - **display_order**: Display priority (lower = shown first)
    """
    return await service.create(entity_id, payload)


@router.put("/{entity_id}/terms/{term_id}", response_model=EntityTermRead)
async def update_entity_term(
    entity_id: UUID,
    term_id: UUID,
    payload: EntityTermWrite,
    service: EntityTermService = Depends(get_entity_term_service),
    user=Depends(get_current_user),
):
    """
    Update an existing term.

    - **entity_id**: The entity UUID
    - **term_id**: The term UUID to update
    - **term**: Updated term text
    - **language**: Updated language code
    - **display_order**: Updated display order
    """
    return await service.update(entity_id, term_id, payload)


@router.delete("/{entity_id}/terms/{term_id}", status_code=204)
async def delete_entity_term(
    entity_id: UUID,
    term_id: UUID,
    service: EntityTermService = Depends(get_entity_term_service),
    user=Depends(get_current_user),
):
    """
    Delete a term from an entity.

    - **entity_id**: The entity UUID
    - **term_id**: The term UUID to delete
    """
    await service.delete(entity_id, term_id)
    return None


@router.put("/{entity_id}/terms-bulk", response_model=List[EntityTermRead])
async def bulk_update_entity_terms(
    entity_id: UUID,
    payload: EntityTermBulkWrite,
    service: EntityTermService = Depends(get_entity_term_service),
    user=Depends(get_current_user),
):
    """
    Replace all terms for an entity.

    Deletes all existing terms and creates new ones from the provided list.
    Useful for entity edit forms where all terms are managed together.

    - **entity_id**: The entity UUID
    - **terms**: List of terms to set (replaces all existing)
    """
    return await service.bulk_update(entity_id, payload.terms)

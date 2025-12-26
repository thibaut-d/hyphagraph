"""
Permission helper functions for authorization.

Implements explicit, readable permission checks.
NO framework magic, NO RBAC abstractions.

Each function clearly states what permission it checks and why.
"""
from fastapi import HTTPException, status
from uuid import UUID

from app.models.user import User
from app.models.relation import Relation


def require_permission(has_permission: bool, message: str = "Permission denied") -> None:
    """
    Raise HTTPException if permission check fails.

    Args:
        has_permission: Boolean result of permission check
        message: Error message to return

    Raises:
        HTTPException 403: If permission is denied
    """
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )


# ============================================================================
# Entity Permissions
# ============================================================================

def can_create_entity(user: User) -> bool:
    """
    Check if user can create entities.

    Current rule: Any active user can create entities.

    Args:
        user: User to check

    Returns:
        True if user can create entities
    """
    return user.is_active


def can_edit_entity(user: User, entity_created_by: UUID | None) -> bool:
    """
    Check if user can edit an entity.

    Current rules:
    - Superusers can edit any entity
    - Users can edit their own entities
    - Users cannot edit entities created by others

    Args:
        user: User to check
        entity_created_by: UUID of user who created the entity (None if unknown)

    Returns:
        True if user can edit the entity
    """
    if user.is_superuser:
        return True

    if entity_created_by is None:
        # Legacy data without attribution - allow active users
        return user.is_active

    return user.id == entity_created_by


# ============================================================================
# Source Permissions
# ============================================================================

def can_create_source(user: User) -> bool:
    """
    Check if user can create sources.

    Current rule: Any active user can create sources.

    Args:
        user: User to check

    Returns:
        True if user can create sources
    """
    return user.is_active


def can_edit_source(user: User, source_created_by: UUID | None) -> bool:
    """
    Check if user can edit a source.

    Current rules:
    - Superusers can edit any source
    - Users can edit their own sources
    - Users cannot edit sources created by others

    Args:
        user: User to check
        source_created_by: UUID of user who created the source (None if unknown)

    Returns:
        True if user can edit the source
    """
    if user.is_superuser:
        return True

    if source_created_by is None:
        # Legacy data without attribution - allow active users
        return user.is_active

    return user.id == source_created_by


# ============================================================================
# Relation Permissions
# ============================================================================

def can_create_relation(user: User) -> bool:
    """
    Check if user can create relations.

    Current rule: Any active user can create relations.

    Args:
        user: User to check

    Returns:
        True if user can create relations
    """
    return user.is_active


def can_edit_relation(user: User, relation_created_by: UUID | None) -> bool:
    """
    Check if user can edit a relation.

    Current rules:
    - Superusers can edit any relation
    - Users can edit their own relations
    - Users cannot edit relations created by others

    Args:
        user: User to check
        relation_created_by: UUID of user who created the relation (None if unknown)

    Returns:
        True if user can edit the relation
    """
    if user.is_superuser:
        return True

    if relation_created_by is None:
        # Legacy data without attribution - allow active users
        return user.is_active

    return user.id == relation_created_by


# ============================================================================
# Inference Permissions
# ============================================================================

def can_publish_inference(user: User) -> bool:
    """
    Check if user can publish inference results.

    Current rule: Only superusers can publish inferences.
    Rationale: Publishing is a privileged operation that affects
    the knowledge base globally.

    Args:
        user: User to check

    Returns:
        True if user can publish inferences
    """
    return user.is_active and user.is_superuser


def can_view_inference(user: User) -> bool:
    """
    Check if user can view inference results.

    Current rule: Any active user can view inferences.

    Args:
        user: User to check

    Returns:
        True if user can view inferences
    """
    return user.is_active


# ============================================================================
# User Management Permissions
# ============================================================================

def can_manage_users(user: User) -> bool:
    """
    Check if user can manage other users.

    Current rule: Only superusers can manage users.

    Args:
        user: User to check

    Returns:
        True if user can manage other users
    """
    return user.is_active and user.is_superuser


def can_view_user(user: User, target_user_id: UUID) -> bool:
    """
    Check if user can view another user's information.

    Current rules:
    - Superusers can view any user
    - Users can view their own information
    - Users cannot view other users' information

    Args:
        user: User to check
        target_user_id: UUID of user to view

    Returns:
        True if user can view the target user
    """
    if user.is_superuser:
        return True

    return user.id == target_user_id

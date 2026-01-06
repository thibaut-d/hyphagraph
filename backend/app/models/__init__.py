"""
Models package - imports all models for easy access and to ensure they're registered with SQLAlchemy.
"""

# Base
from app.models.base import Base

# User and authentication
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.audit_log import AuditLog

# Core data models
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.ui_category import UiCategory

from app.models.source import Source
from app.models.source_revision import SourceRevision

from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision

# Attributes and computed
from app.models.attribute import Attribute
from app.models.computed_relation import ComputedRelation
from app.models.inference_cache import InferenceCache

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "AuditLog",
    "Entity",
    "EntityRevision",
    "EntityTerm",
    "UiCategory",
    "Source",
    "SourceRevision",
    "Relation",
    "RelationRevision",
    "RelationRoleRevision",
    "Attribute",
    "ComputedRelation",
    "InferenceCache",
]

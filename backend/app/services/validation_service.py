from fastapi import HTTPException, status

from app.schemas.relation import RelationWrite
from app.schemas.role import RoleWrite


class ValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


def validate_relation(payload: RelationWrite) -> None:
    # ------------------------------------------------------------
    # 1. Basic required fields
    # ------------------------------------------------------------
    if not payload.source_id:
        _fail("source_id is required")

    if not _non_empty(payload.kind):
        _fail("kind must be a non-empty string")

    # ------------------------------------------------------------
    # 2. Confidence bounds
    # ------------------------------------------------------------
    if payload.confidence is None:
        _fail("confidence is required")

    if not (0.0 <= payload.confidence <= 1.0):
        _fail("confidence must be between 0.0 and 1.0")

    # ------------------------------------------------------------
    # 3. Roles presence
    # ------------------------------------------------------------
    if not payload.roles or len(payload.roles) == 0:
        _fail("relation must have at least one role")

    for role in payload.roles:
        validate_role(role)


def validate_role(role: RoleWrite) -> None:
    if not role.entity_id:
        _fail("role.entity_id is required")

    if not _non_empty(role.role_type):
        _fail("role_type must be a non-empty string")


def _non_empty(value: str | None) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _fail(message: str) -> None:
    raise ValidationError(message)
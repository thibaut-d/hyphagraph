from pydantic import BaseModel


class UserUpdate(BaseModel):
    """Schema for updating user flags from the admin panel."""

    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None


class UserStatsRead(BaseModel):
    """User statistics for the admin dashboard."""

    total_users: int
    active_users: int
    superusers: int
    verified_users: int


class UserListItemRead(BaseModel):
    """User item returned by the admin user endpoints."""

    id: str
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: str

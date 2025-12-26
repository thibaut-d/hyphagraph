from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.models.user import User


class UserRepository:
    """
    Database access layer for User.

    - No business logic
    - No validation
    - No Pydantic
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[User]:
        """List all users ordered by email."""
        stmt = select(User).order_by(User.email)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        """Create a new user."""
        self.db.add(user)
        await self.db.flush()  # assign PK without committing
        return user

    async def update(self, user: User) -> User:
        """Update an existing user."""
        await self.db.flush()
        return user

    async def delete(self, user: User) -> None:
        """Delete a user."""
        await self.db.delete(user)

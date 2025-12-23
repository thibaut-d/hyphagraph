from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_db(session: AsyncSession):
    yield SQLAlchemyUserDatabase(session, User)
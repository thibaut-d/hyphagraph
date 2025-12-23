from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTStrategy, AuthenticationBackend
from fastapi_users.authentication.transport import BearerTransport
from uuid import UUID

from app.models.user import User
from app.auth.user_db import get_user_db
from app.config import settings


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.SECRET_KEY,
        lifetime_seconds=60 * 60 * 24,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=BearerTransport(tokenUrl="auth/jwt/login"),
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, UUID](
    get_user_db,
    [auth_backend],
)
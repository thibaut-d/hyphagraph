from fastapi import APIRouter
from app.auth.auth import auth_backend, fastapi_users
from app.schemas.user import UserRead, UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)
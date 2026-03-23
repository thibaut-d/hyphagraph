from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.schemas.auth import UserRead, UserRegister, UserUpdate
from app.utils.auth import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    hash_token_for_lookup,
    verify_password,
    verify_refresh_token,
)
from app.utils.email import generate_verification_token
from app.services.user.account import (
    authenticate_user,
    change_password as change_user_password,
    create_user,
    deactivate_user,
    delete_user,
    get_user,
    get_user_by_email,
    list_users,
    update_user,
)
from app.services.user.tokens import (
    create_refresh_token_pair,
    refresh_access_token as refresh_token_access_token,
    refresh_access_token_with_user as refresh_token_access_token_with_user,
    revoke_refresh_token as revoke_user_refresh_token,
)
from app.services.user.verification import (
    create_verification_token as create_email_verification_token,
    request_password_reset as request_user_password_reset,
    reset_password as reset_user_password,
    verify_email as verify_user_email,
)


class UserService:
    """Facade for user/account/auth flows split across focused service modules."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def create(self, payload: UserRegister) -> UserRead:
        return await create_user(self, payload, hash_password_fn=hash_password)

    async def get(self, user_id: UUID) -> UserRead:
        return await get_user(self, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await get_user_by_email(self, email)

    async def list_all(self) -> list[UserRead]:
        return await list_users(self)

    async def update(self, user_id: UUID, payload: UserUpdate) -> UserRead:
        return await update_user(self, user_id, payload, hash_password_fn=hash_password)

    async def deactivate(self, user_id: UUID) -> None:
        await deactivate_user(self, user_id)

    async def delete(self, user_id: UUID) -> None:
        await delete_user(self, user_id)

    async def authenticate(self, email: str, password: str) -> User:
        return await authenticate_user(self, email, password, verify_password_fn=verify_password)

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        await change_user_password(
            self,
            user_id,
            current_password,
            new_password,
            verify_password_fn=verify_password,
            hash_password_fn=hash_password,
        )

    async def create_refresh_token(self, user_id: UUID) -> tuple[str, str]:
        return await create_refresh_token_pair(
            self,
            user_id,
            create_access_token_fn=create_access_token,
            generate_refresh_token_fn=generate_refresh_token,
            hash_refresh_token_fn=hash_refresh_token,
            hash_token_for_lookup_fn=hash_token_for_lookup,
        )

    async def refresh_access_token(self, refresh_token: str) -> str:
        return await refresh_token_access_token(
            self,
            refresh_token,
            create_access_token_fn=create_access_token,
            hash_token_for_lookup_fn=hash_token_for_lookup,
            verify_refresh_token_fn=verify_refresh_token,
        )

    async def refresh_access_token_with_user(self, refresh_token: str) -> tuple[str, str, User]:
        return await refresh_token_access_token_with_user(
            self,
            refresh_token,
            create_access_token_fn=create_access_token,
            generate_refresh_token_fn=generate_refresh_token,
            hash_refresh_token_fn=hash_refresh_token,
            hash_token_for_lookup_fn=hash_token_for_lookup,
            verify_refresh_token_fn=verify_refresh_token,
        )

    async def revoke_refresh_token(self, user_id: UUID, refresh_token: str) -> None:
        await revoke_user_refresh_token(
            self,
            user_id,
            refresh_token,
            hash_token_for_lookup_fn=hash_token_for_lookup,
            verify_refresh_token_fn=verify_refresh_token,
        )

    async def create_verification_token(self, user_id: UUID) -> str:
        return await create_email_verification_token(
            self,
            user_id,
            generate_verification_token_fn=generate_verification_token,
        )

    async def verify_email(self, token: str) -> UserRead:
        return await verify_user_email(self, token)

    async def request_password_reset(self, email: str) -> str | None:
        return await request_user_password_reset(
            self,
            email,
            generate_verification_token_fn=generate_verification_token,
        )

    async def reset_password(self, token: str, new_password: str) -> UserRead:
        return await reset_user_password(
            self,
            token,
            new_password,
            hash_password_fn=hash_password,
        )
